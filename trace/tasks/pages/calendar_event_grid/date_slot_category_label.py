"""Calendar-event-grid task for reading a category label from one date slot."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from . import _lifecycle
from .shared.annotations import date_slot_event_chip_box
from .shared.defaults import DOMAIN
from .shared.sampling import build_date_slot_category_case


TASK_ID = "task_pages__calendar_event_grid__date_slot_category_label"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "date_slot_category_label"


def _bind_date_slot_category(selected_branch, branch_probabilities, case, rendered):
    if case.target_date is None:
        raise ValueError("date-slot category case requires a target date")
    prompt_binding = _lifecycle.EventGridPromptBinding(
        prompt_branch_key=PROMPT_QUERY_KEY,
        dynamic_slots={
            "date_number": int(case.target_date),
            "slot_label": str(case.slot_label),
        },
    )
    answer_binding = _lifecycle.string_binding(
        annotation_kind="bbox",
        annotation_value=date_slot_event_chip_box(
            rendered=rendered,
            day=int(case.target_date),
            slot_id=str(case.slot_id),
        ),
        selected_branch=str(selected_branch),
        branch_probabilities=dict(branch_probabilities),
        answer_value=str(case.category_label),
        extra_params={
            "date_number": int(case.target_date),
            "slot_id": str(case.slot_id),
            "slot_label": str(case.slot_label),
            "category_label": str(case.category_label),
        },
    )
    return prompt_binding, answer_binding


@register_task
class PagesCalendarEventGridDateSlotCategoryLabelTask:
    """Return the category shown in a named slot on a named calendar date."""

    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        del max_attempts
        selected_branch, branch_probabilities, task_params = _lifecycle.select_public_branch(
            instance_seed=int(instance_seed),
            params=params,
            supported=SUPPORTED_QUERY_IDS,
            default=SINGLE_QUERY_ID,
            public_task=TASK_ID,
        )
        return _lifecycle.render_bound_event_grid(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            case_factory=build_date_slot_category_case,
            binding_factory=_bind_date_slot_category,
        )


__all__ = ["SUPPORTED_QUERY_IDS", "TASK_ID", "PagesCalendarEventGridDateSlotCategoryLabelTask"]
