# task_games__marble_chain__shot_effect_value

Public taxonomy: `games -> marble_chain -> task_games__marble_chain__shot_effect_value`.

## Program Contract

Program code: `count(existing_chain_marbles_removed_by(marked_shot)); scene=marble_chain; scope=shot_effect_value`.

The scene renders a Zuma-like marble chain with a central shooter marble and one marked shot arrow. The marked shot inserts the shooter marble at the indicated chain gap. If the inserted marble creates a same-color contiguous run of at least three marbles, only existing chain marbles in that run are removed. No later cascade is applied. The task asks for the number of existing chain marbles removed by the marked shot.

Answer schema: `integer`.

Annotation schema: `point_set` containing centers of existing chain marbles that pop; empty when no existing chain marble pops.

Supported `query_id`: `single`.

## Generator

- Implementation: `trace/tasks/games/marble_chain/shot_effect_value.py`
- Config: `configs/domains/games/marble_chain.yaml`
- Prompt bundle: `prompts/games/marble_chain/games_marble_chain_v1.json`
