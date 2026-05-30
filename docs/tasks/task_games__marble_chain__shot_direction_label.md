# `task_games__marble_chain__shot_direction_label`

## Contract
1. Domain: `games`
2. Task group: `marble_chain`
3. Scene id: `marble_chain`
4. Query ids: `max_pop_direction_label`, `target_pop_direction_label`
5. Objective: choose the labeled shot arrow whose single-step marble-chain shot satisfies the requested pop condition.
6. Answer type: `string`.
7. Evidence type: `point_set` containing one point at the insertion gap indicated by the selected arrow.

## Generation Notes
1. The scene shows a Zuma-like board with a central shooter, a shooter marble, and colored marbles on a gray curved or spiral track.
2. Labeled arrows show possible straight shots from the shooter.
3. The single-step rule inserts the shooter marble at the chain gap indicated by the chosen arrow, removes the same-color contiguous run containing it if that run has length at least three, and closes the chain once.
4. The task does not apply recursive cascade removal.
5. `max_pop_direction_label` samples a unique displayed arrow with the largest existing-marble pop count.
6. `target_pop_direction_label` samples a unique displayed arrow with the requested existing-marble pop count.
7. Pop-count answers exclude the shooter marble.
8. Rendering varies shared panel treatment, sampled label font, track layout, and five scene-local track styles before projecting evidence.
