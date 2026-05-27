"""Shared Pool-table geometry helpers for games-domain tasks."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Sequence, Tuple


Point = Tuple[float, float]

TABLE_GEOM_ASPECT = 0.58
POOL_BALL_NUMBERS: Tuple[int, ...] = tuple(range(1, 16))
DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES = 45.0
SUPPORTED_POOL_QUERY_VARIANTS: Tuple[str, ...] = (
    "pottable_ball_count",
    "legal_group_pottable_count",
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

    query_variant: str
    scene_variant: str
    answer: int
    balls: Tuple[PoolBall, ...]
    pockets: Tuple[PoolPocket, ...]
    cue_ball_id: str
    marked_ball_id: str | None
    marked_pocket_id: str | None
    current_player_group: str | None
    evidence_ball_ids: Tuple[str, ...]
    evidence_pocket_ids: Tuple[str, ...]
    pottable_ball_ids: Tuple[str, ...]
    legal_pottable_ball_ids: Tuple[str, ...]
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
    """Return stable id ordering for evidence and trace payloads."""

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


def direct_shot_angle_degrees(*, cue_center: Point, ball_center: Point, pocket_center: Point) -> float:
    """Return the angle between cue-to-ball and ball-to-pocket directions."""

    cue_x, cue_y = _geom(cue_center)
    ball_x, ball_y = _geom(ball_center)
    pocket_x, pocket_y = _geom(pocket_center)
    incoming = (float(ball_x - cue_x), float(ball_y - cue_y))
    outgoing = (float(pocket_x - ball_x), float(pocket_y - ball_y))
    incoming_len = float(math.hypot(*incoming))
    outgoing_len = float(math.hypot(*outgoing))
    if incoming_len <= 1e-12 or outgoing_len <= 1e-12:
        return 180.0
    cosine = max(
        -1.0,
        min(
            1.0,
            ((incoming[0] * outgoing[0]) + (incoming[1] * outgoing[1])) / (incoming_len * outgoing_len),
        ),
    )
    return float(math.degrees(math.acos(cosine)))


def direct_shot_is_aligned(
    *,
    cue_center: Point,
    ball_center: Point,
    pocket_center: Point,
    max_angle_degrees: float = DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES,
) -> bool:
    """Return whether a pocket path is aligned enough for a no-bank direct pot."""

    return direct_shot_angle_degrees(
        cue_center=cue_center,
        ball_center=ball_center,
        pocket_center=pocket_center,
    ) <= float(max_angle_degrees)


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


def line_is_clear(
    *,
    balls: Sequence[PoolBall],
    start: Point,
    end: Point,
    ignore_ball_ids: Iterable[str],
    clearance: float,
) -> bool:
    """Return whether no visible ball blocks a straight shot lane."""

    return not balls_on_segment(
        balls=balls,
        start=start,
        end=end,
        ignore_ball_ids=ignore_ball_ids,
        clearance=float(clearance),
    )


def cue_ball(balls: Sequence[PoolBall], cue_ball_id: str = "cue_ball") -> PoolBall:
    """Return the cue ball from a pool layout."""

    for ball in balls:
        if str(ball.ball_id) == str(cue_ball_id):
            return ball
    raise KeyError("pool layout missing cue ball")


def object_balls(balls: Sequence[PoolBall]) -> Tuple[PoolBall, ...]:
    """Return all non-cue balls."""

    return tuple(ball for ball in balls if not bool(ball.is_cue))


def direct_pocket_ids_for_ball(
    *,
    balls: Sequence[PoolBall],
    pockets: Sequence[PoolPocket],
    cue_ball_id: str,
    ball: PoolBall,
    clearance: float,
    max_angle_degrees: float = DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES,
) -> Tuple[str, ...]:
    """Return pockets reachable by a direct cue-ball shot on one object ball."""

    cue = cue_ball(balls, cue_ball_id=cue_ball_id)
    if not line_is_clear(
        balls=balls,
        start=cue.center,
        end=ball.center,
        ignore_ball_ids=(str(cue.ball_id), str(ball.ball_id)),
        clearance=float(clearance),
    ):
        return tuple()
    reachable: list[str] = []
    for pocket in pockets:
        if direct_shot_is_aligned(
            cue_center=cue.center,
            ball_center=ball.center,
            pocket_center=pocket.center,
            max_angle_degrees=float(max_angle_degrees),
        ) and line_is_clear(
            balls=balls,
            start=ball.center,
            end=pocket.center,
            ignore_ball_ids=(str(ball.ball_id),),
            clearance=float(clearance),
        ):
            reachable.append(str(pocket.pocket_id))
    return tuple(reachable)


def pottable_ball_ids(
    *,
    balls: Sequence[PoolBall],
    pockets: Sequence[PoolPocket],
    cue_ball_id: str,
    clearance: float,
    max_angle_degrees: float = DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES,
) -> Tuple[str, ...]:
    """Return object-ball ids that have at least one direct pocket."""

    return sorted_ids(
        ball.ball_id
        for ball in object_balls(balls)
        if direct_pocket_ids_for_ball(
            balls=balls,
            pockets=pockets,
            cue_ball_id=str(cue_ball_id),
            ball=ball,
            clearance=float(clearance),
            max_angle_degrees=float(max_angle_degrees),
        )
    )


def validate_pool_sample(sample: PoolSample) -> None:
    """Validate that a Pool sample has internally consistent evidence."""

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
    if any(str(ball_id) not in set(ball_ids) for ball_id in sample.evidence_ball_ids):
        raise ValueError("pool ball evidence references unknown ball")
    if any(str(pocket_id) not in set(pocket_ids) for pocket_id in sample.evidence_pocket_ids):
        raise ValueError("pool pocket evidence references unknown pocket")

    query = str(sample.query_variant)
    if query == "pottable_ball_count":
        expected_answer = len(sample.pottable_ball_ids)
        expected_balls = set(sample.pottable_ball_ids)
        expected_pockets: set[str] = set()
    elif query == "legal_group_pottable_count":
        expected_answer = len(sample.legal_pottable_ball_ids)
        expected_balls = set(sample.legal_pottable_ball_ids)
        expected_pockets = set()
    elif query == "blocking_ball_count":
        expected_answer = len(sample.blocking_ball_ids)
        expected_balls = set(sample.blocking_ball_ids)
        expected_pockets = set()
    else:
        raise ValueError(f"unsupported pool query variant: {sample.query_variant}")
    if int(sample.answer) != int(expected_answer):
        raise ValueError("pool answer does not match active query")
    if set(sample.evidence_ball_ids) != expected_balls:
        raise ValueError("pool ball evidence ids do not match active query")
    if set(sample.evidence_pocket_ids) != expected_pockets:
        raise ValueError("pool pocket evidence ids do not match active query")


__all__ = [
    "POOL_BALL_NUMBERS",
    "POOL_POCKETS",
    "DEFAULT_MAX_DIRECT_SHOT_ANGLE_DEGREES",
    "Point",
    "PoolBall",
    "PoolPocket",
    "PoolSample",
    "SUPPORTED_POOL_QUERY_VARIANTS",
    "SUPPORTED_POOL_SCENE_VARIANTS",
    "ball_entity_id",
    "ball_group",
    "balls_on_segment",
    "cue_ball",
    "direct_shot_angle_degrees",
    "direct_shot_is_aligned",
    "direct_pocket_ids_for_ball",
    "line_is_clear",
    "object_balls",
    "pocket_by_id",
    "point_distance",
    "pottable_ball_ids",
    "segment_distance",
    "sorted_ids",
    "validate_pool_sample",
]
