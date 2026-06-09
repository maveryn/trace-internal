"""Shared Pool-table geometry helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence, Tuple


Point = Tuple[float, float]

TABLE_GEOM_ASPECT = 0.58
POOL_BALL_NUMBERS: Tuple[int, ...] = tuple(range(1, 16))
SUPPORTED_POOL_QUERY_IDS: Tuple[str, ...] = (
    "current_group_ball_count",
    "blocking_ball_count",
)
SUPPORTED_POOL_SCENE_VARIANTS: Tuple[str, ...] = ("standard_table",)


@dataclass(frozen=True)
class PoolPocket:
    """One visible pool-table pocket."""

    pocket_id: str
    display_name: str
    center: Point


@dataclass(frozen=True)
class PoolBall:
    """One visible ball on the pool table."""

    ball_id: str
    number: int
    group: str
    center: Point
    is_cue: bool = False
    is_marked: bool = False


@dataclass(frozen=True)
class PoolSample:
    """Generated Pool-table state and query witnesses."""

    query_id: str
    scene_variant: str
    answer: int
    balls: Tuple[PoolBall, ...]
    pockets: Tuple[PoolPocket, ...]
    cue_ball_id: str
    marked_ball_id: str | None
    marked_pocket_id: str | None
    current_player_group: str | None
    annotation_ball_ids: Tuple[str, ...]
    annotation_pocket_ids: Tuple[str, ...]
    blocking_ball_ids: Tuple[str, ...]
    target_answer: int
    construction_mode: str


POOL_POCKETS: Tuple[PoolPocket, ...] = (
    PoolPocket("pocket_top_left", "top-left pocket", (0.035, 0.045)),
    PoolPocket("pocket_top_middle", "top-middle pocket", (0.500, 0.026)),
    PoolPocket("pocket_top_right", "top-right pocket", (0.965, 0.045)),
    PoolPocket("pocket_bottom_left", "bottom-left pocket", (0.035, 0.955)),
    PoolPocket("pocket_bottom_middle", "bottom-middle pocket", (0.500, 0.974)),
    PoolPocket("pocket_bottom_right", "bottom-right pocket", (0.965, 0.955)),
)


def ball_group(number: int) -> str:
    """Return the standard 8-ball group for one object-ball number."""

    value = int(number)
    if value == 0:
        return "cue"
    if value == 8:
        return "eight"
    if 1 <= value <= 7:
        return "solid"
    return "stripe"


def ball_entity_id(number: int) -> str:
    """Return a stable entity id for one ball number."""

    return "cue_ball" if int(number) == 0 else f"ball_{int(number)}"


def pocket_by_id(pockets: Sequence[PoolPocket], pocket_id: str) -> PoolPocket:
    """Return one pocket by id."""

    for pocket in pockets:
        if str(pocket.pocket_id) == str(pocket_id):
            return pocket
    raise KeyError(f"unknown pool pocket id: {pocket_id}")


def sorted_ids(values: Iterable[str]) -> Tuple[str, ...]:
    """Return stable id ordering for annotation and trace payloads."""

    return tuple(sorted(str(value) for value in values))


def _geom(point: Point) -> Point:
    """Map normalized table coordinates to aspect-correct geometry space."""

    x, y = point
    return (float(x), float(y) * float(TABLE_GEOM_ASPECT))


def point_distance(a: Point, b: Point) -> float:
    """Return aspect-correct distance between two normalized table points."""

    ax, ay = _geom(a)
    bx, by = _geom(b)
    return float(math.hypot(float(ax - bx), float(ay - by)))


def segment_distance(point: Point, start: Point, end: Point) -> float:
    """Return aspect-correct point-to-segment distance."""

    px, py = _geom(point)
    ax, ay = _geom(start)
    bx, by = _geom(end)
    vx = float(bx - ax)
    vy = float(by - ay)
    denom = float((vx * vx) + (vy * vy))
    if denom <= 1e-12:
        return float(math.hypot(float(px - ax), float(py - ay)))
    t = max(0.0, min(1.0, (((px - ax) * vx) + ((py - ay) * vy)) / denom))
    qx = float(ax + (t * vx))
    qy = float(ay + (t * vy))
    return float(math.hypot(float(px - qx), float(py - qy)))


def balls_on_segment(
    *,
    balls: Sequence[PoolBall],
    start: Point,
    end: Point,
    ignore_ball_ids: Iterable[str],
    clearance: float,
) -> Tuple[PoolBall, ...]:
    """Return balls whose centers block one straight shot lane."""

    ignored = {str(ball_id) for ball_id in ignore_ball_ids}
    blockers = [
        ball
        for ball in balls
        if str(ball.ball_id) not in ignored
        and segment_distance(ball.center, start, end) <= float(clearance)
        and point_distance(ball.center, start) > float(clearance) * 0.65
        and point_distance(ball.center, end) > float(clearance) * 0.65
    ]
    return tuple(sorted(blockers, key=lambda ball: str(ball.ball_id)))


def object_balls(balls: Sequence[PoolBall]) -> Tuple[PoolBall, ...]:
    """Return all non-cue balls."""

    return tuple(ball for ball in balls if not bool(ball.is_cue))


def validate_pool_sample(sample: PoolSample) -> None:
    """Validate that a Pool sample has internally consistent annotation."""

    ball_ids = [str(ball.ball_id) for ball in sample.balls]
    if len(ball_ids) != len(set(ball_ids)):
        raise ValueError("pool ball ids must be unique")
    pocket_ids = [str(pocket.pocket_id) for pocket in sample.pockets]
    if len(pocket_ids) != len(set(pocket_ids)):
        raise ValueError("pool pocket ids must be unique")
    if str(sample.cue_ball_id) not in set(ball_ids):
        raise ValueError("pool sample missing cue ball")
    if sample.marked_ball_id is not None and str(sample.marked_ball_id) not in set(ball_ids):
        raise ValueError("marked pool ball id is not present")
    if sample.marked_pocket_id is not None and str(sample.marked_pocket_id) not in set(pocket_ids):
        raise ValueError("marked pool pocket id is not present")
    if any(str(ball_id) not in set(ball_ids) for ball_id in sample.annotation_ball_ids):
        raise ValueError("pool ball annotation references unknown ball")
    if any(str(pocket_id) not in set(pocket_ids) for pocket_id in sample.annotation_pocket_ids):
        raise ValueError("pool pocket annotation references unknown pocket")

    query = str(sample.query_id)
    if query == "current_group_ball_count":
        if str(sample.current_player_group) not in {"solid", "stripe"}:
            raise ValueError("current-group pool sample requires solid or stripe group")
        expected_balls = {
            str(ball.ball_id)
            for ball in object_balls(sample.balls)
            if str(ball.group) == str(sample.current_player_group)
        }
        expected_answer = len(expected_balls)
        expected_pockets: set[str] = set()
    elif query == "blocking_ball_count":
        expected_answer = len(sample.blocking_ball_ids)
        expected_balls = set(sample.blocking_ball_ids)
        expected_pockets = set()
    else:
        raise ValueError(f"unsupported pool query id: {sample.query_id}")
    if int(sample.answer) != int(expected_answer):
        raise ValueError("pool answer does not match active query")
    if set(sample.annotation_ball_ids) != expected_balls:
        raise ValueError("pool ball annotation ids do not match active query")
    if set(sample.annotation_pocket_ids) != expected_pockets:
        raise ValueError("pool pocket annotation ids do not match active query")


__all__ = [
    "POOL_BALL_NUMBERS",
    "POOL_POCKETS",
    "Point",
    "PoolBall",
    "PoolPocket",
    "PoolSample",
    "SUPPORTED_POOL_QUERY_IDS",
    "SUPPORTED_POOL_SCENE_VARIANTS",
    "ball_entity_id",
    "ball_group",
    "balls_on_segment",
    "object_balls",
    "pocket_by_id",
    "point_distance",
    "segment_distance",
    "sorted_ids",
    "validate_pool_sample",
]
