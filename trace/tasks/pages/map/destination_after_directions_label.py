"""Pages map task for route-following destination lookup."""

from __future__ import annotations

from typing import Any, Dict

from ...base import TaskOutput
from ...registry import register_task
from .shared.navigation import generate_map_navigation_output


TASK_ID = "task_pages__map__destination_after_directions_label"
QUERY_ID = "destination_after_directions"


@register_task
class PagesMapDestinationAfterDirectionsLabelTask:
    """Identify the destination reached after following visible map directions."""

    task_id = TASK_ID
    domain = "pages"
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        return generate_map_navigation_output(
            public_task_id=self.task_id,
            fixed_query_id=QUERY_ID,
            instance_seed=int(instance_seed),
            params=dict(params),
            max_attempts=int(max_attempts),
        )


__all__ = ["QUERY_ID", "TASK_ID", "PagesMapDestinationAfterDirectionsLabelTask"]
