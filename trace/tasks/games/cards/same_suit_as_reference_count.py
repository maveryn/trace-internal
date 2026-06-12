"""Count non-reference cards with the same suit as the reference card."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.base import TaskOutput
from trace.tasks.games.shared.sampling import resolve_games_named_axis
from trace.tasks.games.shared.style_card_table import SUPPORTED_CARD_STYLE_VARIANTS
from trace.tasks.registry import register_task
from trace.tasks.shared.config_defaults import group_default, load_scene_generation_rendering_prompt_defaults
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID, select_task_query_id
from trace.tasks.shared.output_metadata import default_task_versions
from trace.tasks.shared.prompt_variants import build_prompt_query_spec
from trace.tasks.shared.support_sampling import resolve_integer_choice, resolve_integer_support

from .shared.annotations import card_bboxes_for_ids, keyed_card_bbox_set_map
from .shared.output import build_cards_hand_count_trace_payload, cards_hand_count_trace_params
from .shared.prompts import build_cards_prompt_artifacts
from .shared.rendering import apply_cards_render_overrides, render_cards_task_scene, resolve_cards_render_params
from .shared.sampling import feasible_card_count_support, sample_same_suit_hand
from .shared.state import SCENE_ID


TASK_ID = "task_games__cards__same_suit_as_reference_count"
QUERY_ID = DEFAULT_QUERY_ID
PROMPT_QUERY_KEY = "same_suit_as_reference_count"
SUPPORTED_QUERY_IDS = (QUERY_ID,)
TARGET_ANSWER_SUPPORT = (0, 1, 2, 3, 4, 5)
CARD_COUNT_SUPPORT = (16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26)
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


def _resolve_target_and_card_count(instance_seed: int, params: Mapping[str, Any]) -> tuple[int, tuple[int, ...], Dict[str, float], int, tuple[int, ...], Dict[str, float]]:
    target_answer, target_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="same_suit_target_answer_support",
        explicit_key="target_answer",
        fallback_support=TARGET_ANSWER_SUPPORT,
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        namespace_support_permutation=True,
    )
    target_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="same_suit_target_answer_support",
        fallback=TARGET_ANSWER_SUPPORT,
    )
    raw_card_support = resolve_integer_support(
        params,
        gen_defaults=_GEN_DEFAULTS,
        key="same_suit_as_reference_count_card_count_support",
        fallback=CARD_COUNT_SUPPORT,
    )
    feasible_support = feasible_card_count_support(
        hand_kind=PROMPT_QUERY_KEY,
        target_answer=int(target_answer),
        raw_support=raw_card_support,
    )
    if not feasible_support:
        raise ValueError(f"no feasible card_count values remain for {PROMPT_QUERY_KEY} at target {target_answer}")
    count_params = dict(params)
    count_params["card_count_support"] = [int(value) for value in feasible_support]
    card_count, card_probabilities = resolve_integer_choice(
        instance_seed=int(instance_seed),
        params=count_params,
        gen_defaults=_GEN_DEFAULTS,
        support_key="card_count_support",
        explicit_key="card_count",
        fallback_support=feasible_support,
        namespace=f"{TASK_ID}.card_count",
        balanced_flag_key="balanced_card_count_sampling",
        namespace_support_permutation=True,
    )
    return (
        int(target_answer),
        tuple(int(value) for value in target_support),
        dict(target_probabilities),
        int(card_count),
        tuple(int(value) for value in feasible_support),
        dict(card_probabilities),
    )


@register_task
class GamesCardsSameSuitAsReferenceCountTask:
    """Count non-reference cards with the same suit as the reference card."""

    task_id = TASK_ID
    domain = "games"
    scene_id = SCENE_ID
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        query_id, query_id_probabilities, task_params = select_task_query_id(
            instance_seed=int(instance_seed),
            params=params,
            supported_query_ids=SUPPORTED_QUERY_IDS,
            default_query_id=QUERY_ID,
            task_id=TASK_ID,
            namespace=f"{TASK_ID}.query",
        )
        style_variant, style_probabilities = _resolve_style(int(instance_seed), task_params)
        (
            target_answer,
            target_support,
            target_probabilities,
            card_count,
            card_count_support,
            card_probabilities,
        ) = _resolve_target_and_card_count(int(instance_seed), task_params)
        last_error: ValueError | None = None
        for attempt_index in range(max(1, int(max_attempts))):
            rng = spawn_rng(int(instance_seed), f"{TASK_ID}.attempt.{int(attempt_index)}")
            try:
                sampled_hand = sample_same_suit_hand(
                    rng,
                    card_count=int(card_count),
                    target_answer=int(target_answer),
                    order_by_suit=bool(task_params.get("same_suit_order_by_suit", group_default(_GEN_DEFAULTS, "same_suit_order_by_suit", False))),
                    reference_anchor_index=0,
                )
            except ValueError as exc:
                last_error = exc
                continue
            render_params = resolve_cards_render_params(task_params, instance_seed=int(instance_seed))
            center_label_mode = str(task_params.get("center_label_mode", group_default(_GEN_DEFAULTS, "same_suit_center_label_mode", render_params.center_label_mode)))
            render_params = apply_cards_render_overrides(render_params, {}, center_label_mode=center_label_mode)
            rendered_context = render_cards_task_scene(
                cards=sampled_hand.cards,
                scene_variant="multi_row",
                style_variant=str(style_variant),
                params=task_params,
                instance_seed=int(instance_seed),
                render_params=render_params,
                show_continuation_cue=(PROMPT_QUERY_KEY == "longest_run_length"),
            )
            annotation_bboxes = card_bboxes_for_ids(
                rendered_context.rendered_scene.render_map,
                sampled_hand.annotation_card_ids,
            )
            annotation_gt = TypedValue(type="bbox_set", value=[list(bbox) for bbox in annotation_bboxes])
            projected_annotation = {"bbox_set": [list(bbox) for bbox in annotation_bboxes]}

            prompt_defaults, prompt_artifacts = build_cards_prompt_artifacts(
                domain=self.domain,
                prompt_query_key=PROMPT_QUERY_KEY,
                instance_seed=int(instance_seed),
            )
            answer_gt = TypedValue(type="integer", value=int(target_answer))
            query_spec = build_prompt_query_spec(
                prompt_artifacts=prompt_artifacts,
                query_id=str(query_id),
                params=cards_hand_count_trace_params(
                    sample=sampled_hand,
                    rendered_context=rendered_context,
                    hand_kind=PROMPT_QUERY_KEY,
                    scene_variant="multi_row",
                    style_variant=str(style_variant),
                    target_answer=int(target_answer),
                    target_answer_support=target_support,
                    target_answer_probabilities=target_probabilities,
                    card_count=int(card_count),
                    card_count_support=card_count_support,
                    card_count_probabilities=card_probabilities,
                    style_variant_probabilities=style_probabilities,
                    card_ordering="suit_grouped" if bool(task_params.get("same_suit_order_by_suit", group_default(_GEN_DEFAULTS, "same_suit_order_by_suit", False))) else "sampled",
                    query_id_probabilities=query_id_probabilities,
                ),
            )
            trace_payload = build_cards_hand_count_trace_payload(
                annotation_gt=annotation_gt,
                projected_annotation=projected_annotation,
                sample=sampled_hand,
                rendered_context=rendered_context,
                prompt_defaults=prompt_defaults,
                prompt_artifacts=prompt_artifacts,
                query_spec=query_spec,
                hand_kind=PROMPT_QUERY_KEY,
                scene_variant="multi_row",
                style_variant=str(style_variant),
                target_answer=int(target_answer),
                target_answer_support=target_support,
                target_answer_probabilities=target_probabilities,
                card_count=int(card_count),
                card_count_support=card_count_support,
                card_count_probabilities=card_probabilities,
                style_variant_probabilities=style_probabilities,
                card_ordering="suit_grouped" if bool(task_params.get("same_suit_order_by_suit", group_default(_GEN_DEFAULTS, "same_suit_order_by_suit", False))) else "sampled",
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
                query_id=str(query_id),
            )
        raise RuntimeError(f"{TASK_ID} failed to generate a valid cards hand scene after {max_attempts} attempts") from last_error


__all__ = ["GamesCardsSameSuitAsReferenceCountTask"]
