# task_games__marble_chain__target_pop_direction_label

Public taxonomy: `games -> marble_chain -> task_games__marble_chain__target_pop_direction_label`.

## Program Contract

Program code: `select(labelled_shot_options, condition=immediate_existing_marble_pop_count == target_pop_count); scene=marble_chain; scope=target_pop_direction_label`.

The scene renders a Zuma-like marble chain with a central shooter marble and 4 to 6 labeled shot arrows. A shot inserts the shooter marble at the arrow's indicated chain gap. If the inserted marble creates a same-color contiguous run of at least three marbles, only existing chain marbles in that run are removed. No later cascade is applied. The task asks which displayed arrow removes exactly the target number of existing chain marbles, with a unique displayed answer.

Answer schema: `option_letter`.

Annotation schema: `point_set` containing the selected arrow's insertion-gap point.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/marble_chain/target_pop_direction_label.py`
- Config: `configs/domains/games/marble_chain.yaml`
- Prompt bundle: `prompts/games/marble_chain/games_marble_chain_v1.json`
