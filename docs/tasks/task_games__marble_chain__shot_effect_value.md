# `task_games__marble_chain__shot_effect_value`

## Contract
1. Domain: `games`
2. Task group: `marble_chain`
3. Scene id: `marble_chain`
4. Query ids: `pop_count_after_marked_shot`
5. Objective: compute the numeric pop effect of the marked shot arrow.
6. Answer type: `integer`.
7. Evidence type: `bbox_set` over the marked shot arrow and the affected chain marbles.

## Generation Notes
1. The scene shows a Zuma-like board with a central shooter, a shooter marble, and colored marbles on a gray curved or spiral track.
2. One shot arrow is marked visually.
3. The single-step rule inserts the shooter marble at the chain gap indicated by the marked arrow, removes the same-color contiguous run containing it if that run has length at least three, and closes the chain once.
4. `pop_count_after_marked_shot` counts existing chain marbles removed by the marked shot, excluding the shooter marble.
5. The task does not apply recursive cascade removal.
