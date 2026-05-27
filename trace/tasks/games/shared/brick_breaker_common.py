"""Shared Brick-breaker helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SUPPORTED_BRICK_BREAKER_QUERY_VARIANTS: Tuple[str, ...] = (
    "next_hit_label",
    "paddle_catch_label",
    "hit_row_remaining_count",
)
SUPPORTED_BRICK_BREAKER_SCENE_VARIANTS: Tuple[str, ...] = ("brick_wall",)
SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS: Tuple[str, ...] = (
    "classic",
    "neon",
    "paper",
    "blueprint",
    "arcade",
)


@dataclass(frozen=True)
class BrickBreakerBrick:
    """One visible labeled brick."""

    brick_id: str
    label: str
    row: int
    col: int
    color_index: int


@dataclass(frozen=True)
class BrickBreakerSample:
    """Generated Brick-breaker scene state."""

    brick_rows: int
    brick_cols: int
    lane_count: int
    query_variant: str
    scene_variant: str
    answer: int | str
    bricks: Tuple[BrickBreakerBrick, ...]
    target_brick_id: str | None
    target_brick_label: str | None
    target_row_remaining_brick_ids: Tuple[str, ...]
    target_row_remaining_count: int | None
    target_lane_index: int | None
    target_lane_label: str | None
    ball_start_lane_index: int | None
    evidence_entity_ids: Tuple[str, ...]
    construction_mode: str


def brick_entity_id(row: int, col: int) -> str:
    """Return the stable render/entity id for one brick cell."""

    return f"brick_{int(row)}_{int(col)}"


def lane_entity_id(lane: int) -> str:
    """Return the stable render/entity id for one bottom catch lane pad."""

    return f"lane_{int(lane)}"


def lane_label(lane: int) -> str:
    """Return the prompt-facing label for one catch lane."""

    return chr(ord("A") + int(lane))


def validate_brick_breaker_sample(sample: BrickBreakerSample) -> None:
    """Validate that the generated answer and evidence match the active query."""

    if int(sample.brick_rows) <= 0 or int(sample.brick_cols) <= 0:
        raise ValueError("brick breaker brick grid dimensions must be positive")
    if int(sample.lane_count) <= 0:
        raise ValueError("brick breaker lane_count must be positive")
    brick_ids = [str(brick.brick_id) for brick in sample.bricks]
    brick_labels = [str(brick.label) for brick in sample.bricks]
    if len(brick_ids) != len(set(brick_ids)):
        raise ValueError("brick breaker brick ids must be unique")
    if len(brick_labels) != len(set(brick_labels)):
        raise ValueError("brick breaker brick labels must be unique")
    for brick in sample.bricks:
        if not (0 <= int(brick.row) < int(sample.brick_rows)):
            raise ValueError("brick breaker brick row out of range")
        if not (0 <= int(brick.col) < int(sample.brick_cols)):
            raise ValueError("brick breaker brick col out of range")

    known_entities = set(brick_ids) | {lane_entity_id(lane) for lane in range(int(sample.lane_count))}
    if not set(sample.evidence_entity_ids) <= known_entities:
        raise ValueError("brick breaker evidence references unknown entities")

    query = str(sample.query_variant)
    if query == "next_hit_label":
        if sample.target_brick_id is None or sample.target_brick_label is None:
            raise ValueError("next_hit_label requires a target brick")
        if str(sample.target_brick_id) not in set(brick_ids):
            raise ValueError("target brick id must reference a visible brick")
        if str(sample.target_brick_label) not in set(brick_labels):
            raise ValueError("target brick label must reference a visible brick")
        expected_answer = str(sample.target_brick_label)
        expected_evidence = {str(sample.target_brick_id)}
    elif query == "hit_row_remaining_count":
        if sample.target_brick_id is None:
            raise ValueError("hit_row_remaining_count requires a target brick")
        if str(sample.target_brick_id) not in set(brick_ids):
            raise ValueError("target brick id must reference a visible brick")
        remaining_ids = tuple(str(value) for value in sample.target_row_remaining_brick_ids)
        if sample.target_row_remaining_count is None:
            raise ValueError("hit_row_remaining_count requires a row remaining count")
        if len(remaining_ids) != int(sample.target_row_remaining_count):
            raise ValueError("row remaining id count must match answer")
        if str(sample.target_brick_id) in set(remaining_ids):
            raise ValueError("row remaining evidence must exclude the brick that is hit")
        known_by_id = {str(brick.brick_id): brick for brick in sample.bricks}
        target_row = int(known_by_id[str(sample.target_brick_id)].row)
        for brick_id in remaining_ids:
            if brick_id not in known_by_id:
                raise ValueError("row remaining evidence references unknown brick")
            if int(known_by_id[brick_id].row) != target_row:
                raise ValueError("row remaining evidence must stay in the target row")
        expected_answer = int(sample.target_row_remaining_count)
        expected_evidence = set(remaining_ids)
    elif query == "paddle_catch_label":
        if sample.target_lane_index is None or sample.target_lane_label is None:
            raise ValueError("paddle_catch_label requires a target lane")
        if not (0 <= int(sample.target_lane_index) < int(sample.lane_count)):
            raise ValueError("target lane index out of range")
        expected_answer = str(sample.target_lane_label)
        expected_evidence = {lane_entity_id(int(sample.target_lane_index))}
    else:
        raise ValueError(f"unsupported brick breaker query_variant: {sample.query_variant}")
    if sample.answer != expected_answer:
        raise ValueError("brick breaker answer does not match active query")
    if set(sample.evidence_entity_ids) != expected_evidence:
        raise ValueError("brick breaker evidence ids do not match active query")


__all__ = [
    "SUPPORTED_BRICK_BREAKER_QUERY_VARIANTS",
    "SUPPORTED_BRICK_BREAKER_SCENE_VARIANTS",
    "SUPPORTED_BRICK_BREAKER_STYLE_VARIANTS",
    "BrickBreakerBrick",
    "BrickBreakerSample",
    "brick_entity_id",
    "lane_entity_id",
    "lane_label",
    "validate_brick_breaker_sample",
]
