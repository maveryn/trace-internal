"""Shared Mini-golf helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Tuple


SUPPORTED_MINIGOLF_QUERY_IDS: Tuple[str, ...] = (
    "first_obstacle_label",
    "shot_path_label",
)
SUPPORTED_MINIGOLF_SCENE_VARIANTS: Tuple[str, ...] = ("putting_course",)
SUPPORTED_MINIGOLF_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "desert",
    "neon",
    "garden",
    "blueprint",
)


@dataclass(frozen=True)
class MinigolfObstacle:
    """One visible mini-golf course obstacle."""

    obstacle_id: str
    label: str
    kind: str
    x_norm: float
    y_norm: float
    radius_norm: float
    color_index: int


@dataclass(frozen=True)
class MinigolfShotOption:
    """One labeled shot-direction option."""

    path_id: str
    label: str
    angle_rad: float
    color_index: int


@dataclass(frozen=True)
class MinigolfSample:
    """Generated mini-golf scene state."""

    query_id: str
    scene_variant: str
    style_variant: str
    answer: str
    ball_x_norm: float
    ball_y_norm: float
    hole_x_norm: float
    hole_y_norm: float
    obstacles: Tuple[MinigolfObstacle, ...]
    shot_options: Tuple[MinigolfShotOption, ...]
    target_obstacle_id: str | None
    target_obstacle_label: str | None
    target_path_id: str | None
    target_path_label: str | None
    evidence_entity_ids: Tuple[str, ...]
    construction_mode: str
    cue_visible_fraction: float
    hidden_paths_norm: Mapping[str, Tuple[Tuple[float, float], ...]]


def obstacle_entity_id(index: int) -> str:
    """Return stable entity id for one course obstacle."""

    return f"obstacle_{int(index)}"


def path_entity_id(index: int) -> str:
    """Return stable entity id for one shot option."""

    return f"path_{int(index)}"


def path_label(index: int) -> str:
    """Return a prompt-facing numeric shot label."""

    return str(int(index) + 1)


def validate_minigolf_sample(sample: MinigolfSample) -> None:
    """Validate answer and evidence for one Mini-golf sample."""

    query = str(sample.query_id)
    obstacle_ids = [str(obstacle.obstacle_id) for obstacle in sample.obstacles]
    obstacle_labels = [str(obstacle.label) for obstacle in sample.obstacles]
    path_ids = [str(path.path_id) for path in sample.shot_options]
    path_labels = [str(path.label) for path in sample.shot_options]
    if len(obstacle_ids) != len(set(obstacle_ids)):
        raise ValueError("mini-golf obstacle ids must be unique")
    if len(obstacle_labels) != len(set(obstacle_labels)):
        raise ValueError("mini-golf obstacle labels must be unique")
    if len(path_ids) != len(set(path_ids)):
        raise ValueError("mini-golf path ids must be unique")
    if len(path_labels) != len(set(path_labels)):
        raise ValueError("mini-golf path labels must be unique")

    known_entities = set(obstacle_ids) | set(path_ids) | {"ball", "hole"}
    if not set(sample.evidence_entity_ids) <= known_entities:
        raise ValueError("mini-golf evidence references unknown entities")

    if query == "first_obstacle_label":
        if sample.target_obstacle_id is None or sample.target_obstacle_label is None:
            raise ValueError("first_obstacle_label requires a target obstacle")
        if str(sample.target_obstacle_id) not in set(obstacle_ids):
            raise ValueError("target obstacle id must be visible")
        expected_answer = str(sample.target_obstacle_label)
        expected_evidence = {str(sample.target_obstacle_id)}
    elif query == "shot_path_label":
        if sample.target_path_id is None or sample.target_path_label is None:
            raise ValueError("shot_path_label requires a target path")
        if str(sample.target_path_id) not in set(path_ids):
            raise ValueError("target path id must be visible")
        expected_answer = str(sample.target_path_label)
        expected_evidence = {str(sample.target_path_id)}
    else:
        raise ValueError(f"unsupported mini-golf query_id: {sample.query_id}")

    if str(sample.answer) != str(expected_answer):
        raise ValueError("mini-golf answer does not match active query")
    if set(sample.evidence_entity_ids) != expected_evidence:
        raise ValueError("mini-golf evidence ids do not match active query")


__all__ = [
    "SUPPORTED_MINIGOLF_QUERY_IDS",
    "SUPPORTED_MINIGOLF_SCENE_VARIANTS",
    "SUPPORTED_MINIGOLF_STYLE_VARIANTS",
    "MinigolfObstacle",
    "MinigolfSample",
    "MinigolfShotOption",
    "obstacle_entity_id",
    "path_entity_id",
    "path_label",
    "validate_minigolf_sample",
]
