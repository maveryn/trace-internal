"""Public registration for safe reachable chest counting in RPG dungeons."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import (
    RpgDungeonCountTaskBase,
    build_safe_reachable_chest_count_plan,
    rpg_dungeon_task_defaults,
)


TASK_ID = "task_illustrations__rpg_dungeon__safe_reachable_chest_count"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
_PLAN = build_safe_reachable_chest_count_plan(TASK_ID, SUPPORTED_QUERY_IDS)
_GEN_DEFAULTS, _RENDER_DEFAULTS, _PROMPT_DEFAULTS = rpg_dungeon_task_defaults(TASK_ID)


@register_task
class IllustrationsRpgDungeonSafeReachableChestCountTask(RpgDungeonCountTaskBase):
    """Count reachable chests while excluding monster chambers."""

    task_id = TASK_ID
    supported_query_ids = SUPPORTED_QUERY_IDS
    _plan = _PLAN
    _generation_defaults = _GEN_DEFAULTS
    _rendering_defaults = _RENDER_DEFAULTS
    _prompt_defaults = _PROMPT_DEFAULTS


__all__ = [
    "IllustrationsRpgDungeonSafeReachableChestCountTask",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
]
