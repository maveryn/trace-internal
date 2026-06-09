"""Compatibility imports for misc automaton tasks."""

from __future__ import annotations

from .shared import (
    AGENT_FINAL_TASK_ID,
    AGENT_FLIP_TASK_ID,
    LIFE_GRID_TASK_ID,
    LIFE_POP_TASK_ID,
    TURING_SYMBOL_COUNT_TASK_ID,
    AGENT_SCENE_ID,
    LIFE_SCENE_ID,
    TURING_SCENE_ID,
    AGENT_FINAL_QUERY_IDS,
    AGENT_FLIP_QUERY_IDS,
    LIFE_GRID_QUERY_IDS,
    LIFE_POP_QUERY_IDS,
    TURING_QUERY_IDS,
)
from .agent import (
    MiscAutomatonAgentCellFlipCountTask,
    MiscAutomatonAgentFinalPoseLabelTask,
)
from .life import (
    MiscAutomatonLifeFutureGridLabelTask,
    MiscAutomatonLifePopulationCountTask,
)
from .turing import MiscAutomatonTuringWrittenSymbolCountTask


__all__ = [
    'AGENT_FINAL_TASK_ID',
    'AGENT_FLIP_TASK_ID',
    'LIFE_GRID_TASK_ID',
    'LIFE_POP_TASK_ID',
    'TURING_SYMBOL_COUNT_TASK_ID',
    'AGENT_SCENE_ID',
    'LIFE_SCENE_ID',
    'TURING_SCENE_ID',
    'AGENT_FINAL_QUERY_IDS',
    'AGENT_FLIP_QUERY_IDS',
    'LIFE_GRID_QUERY_IDS',
    'LIFE_POP_QUERY_IDS',
    'TURING_QUERY_IDS',
    'MiscAutomatonAgentFinalPoseLabelTask',
    'MiscAutomatonAgentCellFlipCountTask',
    'MiscAutomatonLifeFutureGridLabelTask',
    'MiscAutomatonLifePopulationCountTask',
    'MiscAutomatonTuringWrittenSymbolCountTask',
]
