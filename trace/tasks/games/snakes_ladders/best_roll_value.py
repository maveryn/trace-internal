from trace.core.seed import spawn_rng
from trace.core.types import TypedValue
from trace.tasks.registry import register_task
from trace.tasks.shared.fixed_query import DEFAULT_QUERY_ID

from ._lifecycle import SnakesLaddersLifecycleTask, SnakesLaddersObjective, run_snakes_ladders_task
from .shared.annotations import bbox_annotation_for_entity
from .shared.rules import square_to_cell_id
from .shared.sampling import construct_best_roll_sample, select_integer_axis
from .shared.state import SUPPORTED_HORIZON_ROLL_COUNTS


TASK_ID = "task_games__snakes_ladders__best_roll_value"
BEST_ROLL_VALUE_SUPPORT = tuple(range(14, 50))
JSON_EXAMPLE = '{"annotation":[554,302,644,392],"answer":49}'
JSON_EXAMPLE_ANSWER_ONLY = '{"answer":49}'


def _prepare_objective(seed, params, axes, _query, _query_probs):
    # Bind the target final square and planning horizon before shared board construction.
    last_square = axes.board_side ** 2
    target, target_probs = select_integer_axis(
        params,
        support_key="best_roll_value_support",
        explicit_key="target_answer",
        fallback_support=BEST_ROLL_VALUE_SUPPORT,
        instance_seed=seed,
        namespace=f"{TASK_ID}.target_answer",
        balanced_flag_key="balanced_target_answer_sampling",
        max_value=last_square,
    )
    horizon, horizon_probs = select_integer_axis(
        params,
        support_key="horizon_roll_count_support",
        explicit_key="horizon_roll_count",
        fallback_support=SUPPORTED_HORIZON_ROLL_COUNTS,
        instance_seed=seed,
        namespace=f"{TASK_ID}.horizon_roll_count",
        balanced_flag_key="balanced_horizon_roll_count_sampling",
    )
    sample = construct_best_roll_sample(
        rng=spawn_rng(seed, f"{TASK_ID}.sample"),
        axes=axes,
        target_final=target,
        horizon=horizon,
    )
    entity_id = square_to_cell_id(sample.answer)
    return SnakesLaddersObjective(
        sample=sample,
        answer_gt=TypedValue(type="integer", value=sample.answer),
        prompt_query_key="best_roll_value",
        json_example=JSON_EXAMPLE,
        json_example_answer_only=JSON_EXAMPLE_ANSWER_ONLY,
        answer_support=[value for value in BEST_ROLL_VALUE_SUPPORT if value <= last_square],
        build_annotation=lambda rendered: bbox_annotation_for_entity(rendered.render_map, entity_id),
        trace_extra_params={
            "target_answer": target,
            "target_answer_probabilities": dict(target_probs),
            "horizon_roll_count": horizon,
            "horizon_roll_count_probabilities": dict(horizon_probs),
            "best_final_square": sample.answer,
        },
        execution_extra={"best_final_square": sample.answer},
        horizon_roll_count=horizon,
    )


@register_task
class GamesSnakesLaddersBestRollValueTask(SnakesLaddersLifecycleTask):
    task_id = TASK_ID

    def generate(self, instance_seed, *, params, max_attempts):
        return run_snakes_ladders_task(
            self,
            instance_seed,
            params,
            max_attempts,
            _prepare_objective,
            supported_query_ids=(DEFAULT_QUERY_ID,),
            default_query_id=DEFAULT_QUERY_ID,
        )
