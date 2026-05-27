"""Bridge-pipe count in a pipe-junction graph."""

from __future__ import annotations

from ...registry import register_task
from ..shared.pipe_junction_task import PipeJunctionGraphTaskBase


@register_task
class GraphCountingPipeBridgeCountTask(PipeJunctionGraphTaskBase):
    """Count open pipes whose removal disconnects part of the open network."""

    task_id = "task_graph__pipe_network__bridge_count"
    task_group = "counting"
    query_id = "pipe_bridge_count"
    prompt_question_key = "question_text_bridge_count"
    prompt_evidence_key = "evidence_hint"
    prompt_task_key_fallback = "bridge_count_query"


__all__ = ["GraphCountingPipeBridgeCountTask"]
