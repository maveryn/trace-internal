"""Shared Platformer helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_PLATFORMER_QUERY_IDS: Tuple[str, ...] = (
    "jump_landing_label",
    "collectible_count",
    "jump_collectible_score_value",
)
SUPPORTED_PLATFORMER_SCENE_VARIANTS: Tuple[str, ...] = ("side_scroller",)
SUPPORTED_PLATFORMER_STYLE_VARIANTS: Tuple[str, ...] = (
    "day",
    "cave",
    "neon",
    "snow",
    "sunset",
)


@dataclass(frozen=True)
class PlatformerPlatform:
    """One visible side-scroller platform."""

    platform_id: str
    label: str
    x_norm: float
    y_norm: float
    width_norm: float
    height_norm: float
    color_index: int


@dataclass(frozen=True)
class PlatformerHazard:
    """One visible side-scroller hazard."""

    hazard_id: str
    label: str
    kind: str
    x_norm: float
    y_norm: float
    width_norm: float
    height_norm: float
    color_index: int


@dataclass(frozen=True)
class PlatformerCollectible:
    """One visible collectible coin/gem."""

    collectible_id: str
    x_norm: float
    y_norm: float
    radius_norm: float
    on_path: bool
    color_index: int
    kind: str = "coin"
    score_value: int | None = None


@dataclass(frozen=True)
class PlatformerSample:
    """Generated platformer scene state."""

    mode: str
    scene_variant: str
    style_variant: str
    answer: str | int
    player_x_norm: float
    player_y_norm: float
    path_points_norm: Tuple[Tuple[float, float], ...]
    visible_path_fraction: float
    platforms: Tuple[PlatformerPlatform, ...]
    hazards: Tuple[PlatformerHazard, ...]
    collectibles: Tuple[PlatformerCollectible, ...]
    target_platform_id: str | None
    target_platform_label: str | None
    target_collectible_ids: Tuple[str, ...]
    annotation_entity_ids: Tuple[str, ...]
    construction_mode: str


def platform_entity_id(index: int) -> str:
    """Return a stable entity id for one platform."""

    return f"platform_{int(index)}"


def hazard_entity_id(index: int) -> str:
    """Return a stable entity id for one hazard."""

    return f"hazard_{int(index)}"


def collectible_entity_id(index: int) -> str:
    """Return a stable entity id for one collectible."""

    return f"collectible_{int(index)}"


def validate_platformer_sample(sample: PlatformerSample) -> None:
    """Validate answer and annotation for one Platformer sample."""

    platform_ids = [str(platform.platform_id) for platform in sample.platforms]
    platform_labels = [str(platform.label) for platform in sample.platforms if str(platform.label)]
    hazard_ids = [str(hazard.hazard_id) for hazard in sample.hazards]
    hazard_labels = [str(hazard.label) for hazard in sample.hazards if str(hazard.label)]
    collectible_ids = [str(collectible.collectible_id) for collectible in sample.collectibles]
    if len(platform_ids) != len(set(platform_ids)):
        raise ValueError("platform ids must be unique")
    if len(platform_labels) != len(set(platform_labels)):
        raise ValueError("platform labels must be unique")
    if len(hazard_ids) != len(set(hazard_ids)):
        raise ValueError("hazard ids must be unique")
    if len(hazard_labels) != len(set(hazard_labels)):
        raise ValueError("hazard labels must be unique")
    if len(collectible_ids) != len(set(collectible_ids)):
        raise ValueError("collectible ids must be unique")

    known_entities = set(platform_ids) | set(hazard_ids) | set(collectible_ids) | {"player"}
    if not set(sample.annotation_entity_ids) <= known_entities:
        raise ValueError("platformer annotation references unknown entities")

    query = str(sample.mode)
    if query == "jump_landing_label":
        if sample.target_platform_id is None or sample.target_platform_label is None:
            raise ValueError("jump_landing_label requires a target platform")
        expected_answer: str | int = str(sample.target_platform_label)
        expected_annotation = {str(sample.target_platform_id)}
    elif query == "collectible_count":
        expected_answer = int(len(sample.target_collectible_ids))
        expected_annotation = set(str(value) for value in sample.target_collectible_ids)
    elif query == "jump_collectible_score_value":
        collectible_by_id = {str(collectible.collectible_id): collectible for collectible in sample.collectibles}
        expected_annotation = set(str(value) for value in sample.target_collectible_ids)
        if not expected_annotation:
            raise ValueError("jump_collectible_score_value requires scored collectibles")
        saw_coin = False
        saw_bonus = False
        score_total = 0
        for collectible_id in expected_annotation:
            collectible = collectible_by_id.get(str(collectible_id))
            if collectible is None:
                raise ValueError("jump_collectible_score_value target references unknown collectible")
            if not bool(collectible.on_path):
                raise ValueError("jump_collectible_score_value target collectibles must lie on the jump arc")
            if collectible.score_value is None:
                score_total += 1
                saw_coin = True
            else:
                if int(collectible.score_value) <= 0:
                    raise ValueError("jump_collectible_score_value bonus scores must be positive")
                score_total += int(collectible.score_value)
                saw_bonus = True
        if not saw_coin or not saw_bonus:
            raise ValueError("jump_collectible_score_value requires at least one coin and one bonus item")
        expected_answer = int(score_total)
    else:
        raise ValueError(f"unsupported platformer mode: {sample.mode}")

    if sample.answer != expected_answer:
        raise ValueError("platformer answer does not match active query")
    if set(sample.annotation_entity_ids) != expected_annotation:
        raise ValueError("platformer annotation ids do not match active query")


__all__ = [
    "SUPPORTED_PLATFORMER_QUERY_IDS",
    "SUPPORTED_PLATFORMER_SCENE_VARIANTS",
    "SUPPORTED_PLATFORMER_STYLE_VARIANTS",
    "PlatformerCollectible",
    "PlatformerHazard",
    "PlatformerPlatform",
    "PlatformerSample",
    "collectible_entity_id",
    "hazard_entity_id",
    "platform_entity_id",
    "validate_platformer_sample",
]
