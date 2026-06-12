"""Return the unique min/max completed-line sum on a visible Bingo card."""
from __future__ import annotations
from trace.tasks.registry import register_task
from ._lifecycle import BingoAttemptResult, BingoObjectivePlan, bingo_named_count_trace_params, resolve_bingo_task_float_param, resolve_bingo_task_integer_target, run_bingo_lifecycle
from .shared.annotations import line_sum_target_cell_ids
from .shared.sampling import resolve_bingo_extremum, resolve_bingo_line_axis
from .shared.rules import build_line_sum_extremum_card_state
from .shared.defaults import SCENE_ID
TASK_ID = 'task_games__bingo__line_sum_extremum_value'
QUERY_ID = 'line_sum_extremum_value'
SUPPORTED_QUERY_IDS = (QUERY_ID,)
LINE_SUM_COMPLETED_LINE_COUNT_SUPPORT = (2, 3, 4)

def _prepare_line_sum_objective(instance_seed, task_params, _query_id, _query_probabilities):
    """Resolve extremum-sum semantics and bind unique completed-line construction."""
    line_axis, line_axis_probabilities = resolve_bingo_line_axis(int(instance_seed), params=task_params)
    extremum, extremum_probabilities = resolve_bingo_extremum(int(instance_seed), params=task_params)
    completed_line_target = resolve_bingo_task_integer_target(instance_seed=int(instance_seed), task_id=TASK_ID, task_params=task_params, support_key='line_sum_completed_line_count_support', fallback_support=LINE_SUM_COMPLETED_LINE_COUNT_SUPPORT, namespace=f'{TASK_ID}.completed_line_count')
    distractor_mark_prob = resolve_bingo_task_float_param(task_id=TASK_ID, task_params=task_params, key='line_sum_distractor_mark_prob', fallback=0.2)

    def construct_attempt(rng, _axes):
        card_state = build_line_sum_extremum_card_state(rng=rng, line_axis=str(line_axis), extremum=str(extremum), completed_line_count=int(completed_line_target.target_answer), distractor_mark_prob=float(distractor_mark_prob))
        if card_state.line_sum_target_value is None:
            raise ValueError('line-sum construction must bind a target value')
        annotation_cell_ids = line_sum_target_cell_ids(card_state)
        return BingoAttemptResult(card_state=card_state, answer_value=int(card_state.line_sum_target_value), annotation_cell_ids=annotation_cell_ids, execution_extra={'line_axis': str(line_axis), 'extremum': str(extremum), 'completed_line_count_target': int(completed_line_target.target_answer), 'line_sum_distractor_mark_prob': float(distractor_mark_prob)})
    return BingoObjectivePlan(attempt_namespace=f'games.bingo.{TASK_ID}', prompt_query_key=QUERY_ID, prompt_dynamic_slots={'line_axis': str(line_axis), 'extremum': str(extremum)}, query_params={'line_axis': str(line_axis), 'line_axis_probabilities': dict(line_axis_probabilities), 'extremum': str(extremum), 'extremum_probabilities': dict(extremum_probabilities), **bingo_named_count_trace_params('completed_line_count', completed_line_target), 'line_sum_distractor_mark_prob': float(distractor_mark_prob)}, construct_attempt=construct_attempt)

@register_task
class GamesBingoLineSumExtremumValueTask:
    task_id = TASK_ID
    domain = 'games'
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_bingo_lifecycle(task_id=TASK_ID, supported_query_ids=SUPPORTED_QUERY_IDS, instance_seed=int(instance_seed), params=params, max_attempts=int(max_attempts), prepare_objective=_prepare_line_sum_objective)
