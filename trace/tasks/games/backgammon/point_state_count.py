"""Count Backgammon points matching one checker stack-state predicate."""
from __future__ import annotations
from trace.tasks.base import TaskOutput
from trace.tasks.registry import register_task
from ._lifecycle import BackgammonObjectivePlan, integer_count_attempt_result, resolve_backgammon_count_target, run_backgammon_lifecycle
from .shared.sampling import sample_point_state_count_scene
from .shared.state import PLAYER_BLACK, PLAYER_WHITE, SCENE_ID, STACK_STATE_SINGLE, STACK_STATE_TWO_OR_MORE
TASK_ID = 'task_games__backgammon__point_state_count'
POINT_STATE_COUNT_SUPPORT = (0, 1, 2, 3, 4, 5, 6)
POINT_STATE_QUERY_SPECS: dict[str, tuple[str, str]] = {'black_single_checker_point_count': (PLAYER_BLACK, STACK_STATE_SINGLE), 'white_single_checker_point_count': (PLAYER_WHITE, STACK_STATE_SINGLE), 'black_two_or_more_checker_point_count': (PLAYER_BLACK, STACK_STATE_TWO_OR_MORE), 'white_two_or_more_checker_point_count': (PLAYER_WHITE, STACK_STATE_TWO_OR_MORE)}
SUPPORTED_QUERY_IDS = tuple(POINT_STATE_QUERY_SPECS)

def _prepare_point_state_objective(instance_seed, task_params, query_id):
    """Resolve the checker-stack predicate and bind exact-count sample construction."""
    checker_color, stack_state = POINT_STATE_QUERY_SPECS[str(query_id)]
    target = resolve_backgammon_count_target(instance_seed=int(instance_seed), task_params=task_params, task_id=TASK_ID, support_key='point_state_count_support', fallback_support=POINT_STATE_COUNT_SUPPORT, namespace=f'backgammon.point_state_count.{str(query_id)}.target_answer')

    def construct_attempt(rng, axes):
        sample = sample_point_state_count_scene(rng, axes=axes, checker_color=str(checker_color), stack_state=str(stack_state), target_answer=int(target.target_answer))
        return integer_count_attempt_result(sample=sample, target_points=tuple((int(point) for point in sample.target_points)), construction_mode='exact_point_state_count')
    return BackgammonObjectivePlan(attempt_namespace='games.backgammon.point_state_count', query_params={'target_answer_support': [int(value) for value in target.target_answer_support], 'target_answer_probabilities': dict(target.target_answer_probabilities)}, construct_attempt=construct_attempt)

@register_task
class GamesBackgammonPointStateCountTask:
    """Count numbered Backgammon points by checker color and stack state."""
    task_id = TASK_ID
    domain = 'games'
    default_dataset_enabled = True
    supported_query_ids = SUPPORTED_QUERY_IDS

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int) -> TaskOutput:
        """Generate a stack-state count board by binding color and stack predicate locally."""
        return run_backgammon_lifecycle(task_id=self.task_id, supported_query_ids=SUPPORTED_QUERY_IDS, instance_seed=int(instance_seed), params=params, max_attempts=int(max_attempts), prepare_objective=_prepare_point_state_objective)
__all__ = ['GamesBackgammonPointStateCountTask']
