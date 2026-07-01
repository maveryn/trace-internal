from __future__ import annotations

from typing import Any, Mapping

from trace.core.query_ids import SINGLE_QUERY_ID
from trace.tasks.registry import register_task

from . import _lifecycle
from .shared.annotations import field_value_bbox, lookup_supporting_bboxes
from .shared.defaults import DOMAIN
from .shared.sampling import select_text_field_target


TASK_ID = "task_pages__profile_card_grid__value_for_named_profile_field"
PROMPT_QUERY_KEY = "value_for_named_profile_field"
SUPPORTED_QUERY_IDS = (SINGLE_QUERY_ID,)


def _bind_value_for_named_profile_field(
    instance_seed: int,
    params: Mapping[str, Any],
    selected_branch: str,
    branch_probabilities: Mapping[str, float],
    case,
    rendered,
):
    """Bind named-profile field lookup to the selected value bbox."""

    card, field_label = select_text_field_target(
        params=params,
        instance_seed=int(instance_seed),
        cards=case.spec.cards,
        namespace=TASK_ID,
    )
    field_value = str(card.fields[str(field_label)])
    target_payload = {
        "profile_id": str(card.profile_id),
        "profile_name": str(card.name),
        "field_label": str(field_label),
        "field_value": str(field_value),
    }
    return (
        _lifecycle.ProfileCardPromptBinding(
            prompt_branch_key=PROMPT_QUERY_KEY,
            dynamic_slots={
                "profile_name": str(card.name),
                "field_label": str(field_label),
            },
        ),
        _lifecycle.string_binding(
            annotation_bbox=field_value_bbox(
                card=card,
                field_label=str(field_label),
                rendered=rendered.rendered_grid,
            ),
            supporting_bboxes=lookup_supporting_bboxes(
                card=card,
                field_label=str(field_label),
                rendered=rendered.rendered_grid,
            ),
            selected_branch=str(selected_branch),
            branch_probabilities=branch_probabilities,
            answer_value=str(field_value),
            target_payload=target_payload,
            question_format="profile_card_grid_value_for_named_profile_field",
        ),
    )


@register_task
class PagesProfileCardGridValueForNamedProfileFieldTask:
    task_id = TASK_ID
    domain = DOMAIN
    supported_query_ids = SUPPORTED_QUERY_IDS
    default_dataset_enabled = True

    def generate(self, instance_seed: int, *, params: Mapping[str, Any], max_attempts: int):
        del max_attempts
        selected_branch, branch_probabilities, task_params = _lifecycle.select_public_branch(
            instance_seed=int(instance_seed),
            params=params,
            supported=SUPPORTED_QUERY_IDS,
            default=SINGLE_QUERY_ID,
            public_task=TASK_ID,
        )
        return _lifecycle.render_bound_profile_card_grid(
            instance_seed=int(instance_seed),
            params=task_params,
            selected_branch=selected_branch,
            branch_probabilities=branch_probabilities,
            include_numeric_fields=False,
            binding_factory=_bind_value_for_named_profile_field,
        )
