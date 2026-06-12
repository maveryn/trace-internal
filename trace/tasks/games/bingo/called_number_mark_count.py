"""Count called Bingo numbers that are currently marked on the card."""
from __future__ import annotations
from trace.tasks.registry import register_task
from ._lifecycle import BingoAttemptResult, BingoObjectivePlan, bingo_named_count_trace_params, bingo_target_trace_params, resolve_bingo_task_float_param, resolve_bingo_task_integer_target, run_bingo_lifecycle
from .shared.annotations import called_marked_cell_ids
from .shared.rules import build_called_marked_number_card_state
from .shared.defaults import SCENE_ID
TASK_ID = 'task_games__bingo__called_number_mark_count'
QUERY_ID = 'called_marked_number_count'
SUPPORTED_QUERY_IDS = (QUERY_ID,)
CALLED_MARKED_NUMBER_COUNT_SUPPORT = (0, 1, 2, 3, 4, 5)
CALLED_NUMBER_COUNT_SUPPORT = (5, 6, 7, 8)

def _prepare_called_number_objective(instance_seed, task_params, _query_id, _query_probabilities):
    """Resolve called-number count axes and bind marked-called-cell construction."""
    target_axis = resolve_bingo_task_integer_target(instance_seed=int(instance_seed), task_id=TASK_ID, task_params=task_params, support_key='called_marked_number_count_support', fallback_support=CALLED_MARKED_NUMBER_COUNT_SUPPORT, namespace=f'{TASK_ID}.target_answer')
    called_count_axis = resolve_bingo_task_integer_target(instance_seed=int(instance_seed), task_id=TASK_ID, task_params=task_params, support_key='called_number_count_support', fallback_support=CALLED_NUMBER_COUNT_SUPPORT, namespace=f'{TASK_ID}.called_number_count', explicit_key='called_number_count', balanced_flag_key='balanced_called_number_count_sampling')
    distractor_mark_prob = resolve_bingo_task_float_param(task_id=TASK_ID, task_params=task_params, key='axis_distractor_mark_prob', fallback=0.2)

    def construct_attempt(rng, _axes):
        card_state = build_called_marked_number_card_state(rng=rng, marked_called_count=int(target_axis.target_answer), called_number_count=int(called_count_axis.target_answer), distractor_mark_prob=float(distractor_mark_prob))
        annotation_cell_ids = called_marked_cell_ids(card_state)
        return BingoAttemptResult(card_state=card_state, answer_value=int(target_axis.target_answer), annotation_cell_ids=annotation_cell_ids, execution_extra={'called_number_count': int(called_count_axis.target_answer), 'axis_distractor_mark_prob': float(distractor_mark_prob)})
    return BingoObjectivePlan(attempt_namespace=f'games.bingo.{TASK_ID}', prompt_query_key=QUERY_ID, show_called_panel=True, query_params={**bingo_target_trace_params(target_axis), **bingo_named_count_trace_params('called_number_count', called_count_axis), 'axis_distractor_mark_prob': float(distractor_mark_prob)}, construct_attempt=construct_attempt)

@register_task
class GamesBingoCalledNumberMarkCountTask:
    task_id = TASK_ID
    domain = 'games'
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_bingo_lifecycle(task_id=TASK_ID, supported_query_ids=SUPPORTED_QUERY_IDS, instance_seed=int(instance_seed), params=params, max_attempts=int(max_attempts), prepare_objective=_prepare_called_number_objective)
