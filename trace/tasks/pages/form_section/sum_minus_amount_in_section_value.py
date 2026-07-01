"""Form-section task for a two-term sum followed by one subtraction."""

from __future__ import annotations

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from ._lifecycle import run_form_section_public_entry
from .shared.sampling import ExpressionPlan, SCENE_VARIANTS


TASK_ID = "task_pages__form_section__sum_minus_amount_in_section_value"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)
PROMPT_QUERY_KEY = "sum_minus_amount_in_section_value"
QUESTION_FORMAT = "form_section_sum_minus_amount_in_section_value"
REASONING_LOAD_BASE = 0.44


def _build_expression_plan() -> ExpressionPlan:
    """Bind this public task to three operands with add-then-subtract order."""

    return ExpressionPlan(
        operation_name="sum_minus_amount_in_section",
        operand_count=3,
        operators=("+", "-"),
    )


@register_task
class PagesFormSectionSumMinusAmountInSectionValueTask:
    """Compute amount plus amount minus amount in one named section."""

    task_id = TASK_ID
    domain = "pages"
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed, *, params, max_attempts):
        return run_form_section_public_entry(
            instance_seed=int(instance_seed),
            params=params,
            max_attempts=int(max_attempts),
            public_task=TASK_ID,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            expression=_build_expression_plan(),
            prompt_query_key=PROMPT_QUERY_KEY,
            question_format=QUESTION_FORMAT,
            reasoning_load_base=REASONING_LOAD_BASE,
        )


__all__ = [
    "PROMPT_QUERY_KEY",
    "QUESTION_FORMAT",
    "SCENE_VARIANTS",
    "SUPPORTED_QUERY_IDS",
    "TASK_ID",
    "PagesFormSectionSumMinusAmountInSectionValueTask",
]
