from __future__ import annotations

from trace.core.seed import spawn_rng
from trace.tasks.registry import register_task

from ._lifecycle import SnakeLifecycleTask, build_integer_snake_objective, run_snake_task, select_snake_integer_target
from .shared.defaults import DEFAULTS
from .shared.rules import coord_to_cell_id, shortest_static_path_to_food, validate_snake_state
from .shared.sampling import open_cells, random_snake_state, sample_obstacles, with_food, with_obstacles
from .shared.state import SnakeSample


TASK_ID = "task_games__snake__shortest_food_path_length"
PROMPT_KEY = "shortest_food_path_length"


def _prepare_shortest_path_objective(attempt_seed, task_params, axes):
    # Role: construct a board whose food is reachable in exactly the target path length.
    target, target_probabilities = select_snake_integer_target(
        task_params,
        objective_key=PROMPT_KEY,
        fallback_support=DEFAULTS.shortest_food_path_length_support,
        instance_seed=int(attempt_seed),
        namespace=TASK_ID,
    )
    rng = spawn_rng(int(attempt_seed), f"{TASK_ID}.sample")
    for _attempt in range(900):
        state = random_snake_state(rng=rng, board_size=int(axes.board_size), body_length=int(axes.body_length))
        try:
            obstacles = sample_obstacles(rng=rng, state=state, count=int(axes.obstacle_count))
        except ValueError:
            continue
        state = with_obstacles(state, obstacles)
        validate_snake_state(state)
        candidate_food = list(open_cells(state))
        rng.shuffle(candidate_food)
        for food in candidate_food:
            candidate_state = with_food(state, food)
            shortest_path = shortest_static_path_to_food(candidate_state)
            if shortest_path is None or len(shortest_path) != int(target):
                continue
            annotation_cell_ids = tuple(coord_to_cell_id(coord) for coord in shortest_path)
            sample = SnakeSample(
                answer=int(len(shortest_path)),
                state=candidate_state,
                annotation_cell_ids=annotation_cell_ids,
                construction_mode=f"shortest_food_path_length_{int(target)}",
                shortest_path_coords=tuple(shortest_path),
            )
            return build_integer_snake_objective(
                sample=sample,
                prompt_key=PROMPT_KEY,
                prompt_json_example_answer=4,
                prompt_json_example_annotation_count=4,
                answer_support=list(DEFAULTS.shortest_food_path_length_support),
                annotation_cell_ids=tuple(sample.annotation_cell_ids),
                target_trace_key="target_shortest_food_path_length",
                target_value=int(target),
                target_probabilities=target_probabilities,
            )
    raise ValueError("failed to construct Snake shortest-food-path sample")


@register_task
class GamesSnakeShortestFoodPathLengthTask(SnakeLifecycleTask):
    task_id = TASK_ID

    def generate(self, instance_seed: int, *, params: dict, max_attempts: int):
        return run_snake_task(self, instance_seed, params, max_attempts, _prepare_shortest_path_objective)
