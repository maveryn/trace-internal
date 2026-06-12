"""GamesCardsPokerDrawCardLabelTask cards task."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Sequence

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.style_card_table import SUPPORTED_CARD_STYLE_VARIANTS
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from .shared.annotations import card_bboxes_for_ids
from .shared.output import build_cards_rule_trace_payload, cards_rule_trace_params
from .shared.prompts import build_cards_prompt_artifacts
from .shared.rendering import apply_cards_render_overrides, render_cards_task_scene, resolve_cards_render_params
from .shared.sampling import (
    SUPPORTED_POKER_DRAW_TARGET_CATEGORIES,
    sample_poker_draw_card,
    target_candidate_index,
)
from .shared.state import SCENE_ID


TASK_ID = "task_games__cards__poker_draw_card_label"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "poker_draw_card_label"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
POKER_DRAW_CANDIDATE_COUNT_SUPPORT = (4, 6)
_GEN_DEFAULTS, _RENDER_DEFAULTS_UNUSED, _PROMPT_DEFAULTS_UNUSED = load_scene_generation_rendering_prompt_defaults(
    "games",
    SCENE_ID,
    task_id=TASK_ID,
)


def _resolve_style(instance_seed: int, params: Mapping[str, Any]) -> tuple[str, Dict[str, float]]:
    return resolve_games_named_axis(
        task_id=TASK_ID,
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        namespace="style_variant",
        explicit_key="style_variant",
        weights_key="style_variant_weights",
        balance_flag_key="balanced_style_variant_sampling",
        supported_variants=SUPPORTED_CARD_STYLE_VARIANTS,
    )


def _resolve_integer_axis(
    instance_seed: int,
    params: Mapping[str, Any],
    *,
    support_key: str,
    explicit_key: str,
    fallback_support: Sequence[int],
    namespace: str,
    balanced_flag_key: str = "balanced_option_count_sampling",
) -> tuple[int, tuple[int, ...], Dict[str, float]]:
    support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key=str(support_key),
        fallback=tuple(int(value) for value in fallback_support),
    )
    axis_params = dict(params)
    axis_params[f"{explicit_key}_support"] = [int(value) for value in support]
    value, probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=axis_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key=f"{explicit_key}_support",
        explicit_key=str(explicit_key),
        fallback_support=support,
        namespace=str(namespace),
        balanced_flag_key=str(balanced_flag_key),
        namespace_support_permutation=True,
    )
    return int(value), tuple(int(item) for item in support), dict(probabilities)


def _render_and_return(
    *,
    self_obj,
    instance_seed: int,
    task_params: Mapping[str, Any],
    style_variant: str,
    style_probabilities: Mapping[str, float],
    sample,
    runtime_query_id: str,
    prompt_query_key: str,
    query_params: Mapping[str, Any],
) -> TaskOutput:
    render_params = resolve_cards_render_params(task_params, instance_seed=int(instance_seed))
    render_params = apply_cards_render_overrides(
        render_params,
        sample.render_overrides,
        center_label_mode=str(sample.center_label_mode),
        max_cards_per_row=int(sample.cards_per_row),
    )
    rendered_context = render_cards_task_scene(
        cards=sample.cards,
        scene_variant=str(sample.scene_variant),
        style_variant=str(style_variant),
        params=task_params,
        instance_seed=int(instance_seed),
        render_params=render_params,
        show_continuation_cue=False,
        row_card_counts=sample.row_card_counts if sample.row_card_counts else None,
    )
    annotation_bboxes = card_bboxes_for_ids(
        rendered_context.rendered_scene.render_map,
        sample.annotation_card_ids,
    )
    prompt_defaults, prompt_artifacts = build_cards_prompt_artifacts(
        domain=self_obj.domain,
        prompt_query_key=str(prompt_query_key),
        dynamic_slots={str(key): str(value) for key, value in sample.prompt_slots.items()},
        instance_seed=int(instance_seed),
    )
    answer_gt = TypedValue(type="string", value=str(sample.answer))
    annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
    query_spec = build_prompt_query_spec(
        prompt_artifacts=prompt_artifacts,
        query_id=str(runtime_query_id),
        params=cards_rule_trace_params(
            sample=sample,
            rendered_context=rendered_context,
            style_variant=str(style_variant),
            style_variant_probabilities=style_probabilities,
            extra_trace_params=dict(query_params),
        ),
    )
    trace_payload = build_cards_rule_trace_payload(
        annotation_gt=annotation_gt,
        sample=sample,
        rendered_context=rendered_context,
        prompt_defaults=prompt_defaults,
        prompt_artifacts=prompt_artifacts,
        query_spec=query_spec,
        style_variant=str(style_variant),
        style_variant_probabilities=style_probabilities,
    )
    return TaskOutput(
        prompt=str(prompt_artifacts.prompt),
        prompt_variants=dict(prompt_artifacts.prompt_variants),
        answer_gt=answer_gt,
        annotation_gt=annotation_gt,
        image=rendered_context.image,
        image_id="img0",
        trace_payload=trace_payload,
        task_versions=default_task_versions(),
        scene_id=SCENE_ID,
        query_id=str(runtime_query_id),
    )


@register_task
class GamesCardsPokerDrawCardLabelTask:
    """Generate the poker_draw_card_label card-rule task."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        runtime_query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        style_variant, style_probabilities = _resolve_style(int(instance_seed), task_params)
        candidate_count, candidate_count_support, candidate_count_probs = _resolve_integer_axis(
            int(instance_seed),
            task_params,
            support_key="poker_draw_candidate_count_support",
            explicit_key="option_count",
            fallback_support=POKER_DRAW_CANDIDATE_COUNT_SUPPORT,
            namespace=f"{TASK_ID}.candidate_count",
        )
        target_category, target_category_probs = resolve_games_named_axis(
            task_id=TASK_ID,
            instance_seed=int(instance_seed),
            params=task_params,
            gen_defaults=_GEN_DEFAULTS,
            namespace="poker_draw_target_category",
            explicit_key="poker_draw_target_category",
            weights_key="poker_draw_target_category_weights",
            balance_flag_key="balanced_poker_draw_target_category_sampling",
            supported_variants=SUPPORTED_POKER_DRAW_TARGET_CATEGORIES,
        )
        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sample = sample_poker_draw_card(
                    rng,
                    candidate_count=int(candidate_count),
                    target_category_key=str(target_category),
                    target_index=target_candidate_index(rng=rng, params=task_params, candidate_count=int(candidate_count)),
                    candidate_count_support=candidate_count_support,
                    candidate_count_probabilities=candidate_count_probs,
                    target_category_probabilities=target_category_probs,
                )
            except ValueError as exc:
                last_error = exc
                continue
            return _render_and_return(
                self_obj=self,
                instance_seed=int(instance_seed),
                task_params=task_params,
                style_variant=str(style_variant),
                style_probabilities=style_probabilities,
                sample=sample,
                runtime_query_id=str(runtime_query_id),
                prompt_query_key=PROMPT_QUERY_KEY,
                query_params={"query_id_probabilities": dict(query_id_probabilities)},
            )
        raise RuntimeError(f"{TASK_ID} failed to generate a valid poker draw scene") from last_error


__all__ = ["GamesCardsPokerDrawCardLabelTask"]
