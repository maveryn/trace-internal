# `task_games__match3__best_swap_label`

## Contract
1. Domain: `games`
2. Task group: `match3`
3. Scene id: `match3`
4. Query ids: `max_clear_swap_label`, `target_clear_swap_label`
5. Objective: choose the labeled adjacent-swap arrow whose immediate match-3 clear effect satisfies the requested condition.
6. Answer type: `string`.
7. Evidence type: `bbox_set` over the selected arrow and the affected gems.

## Generation Notes
1. The scene shows a match-3 board with row/column numbers, colored gems, and labeled adjacent-swap arrows.
2. The board has no matching runs before the selected swap.
3. The rule applies one adjacent swap, then clears every horizontal or vertical run of at least three matching gems.
4. The task does not apply gravity, refill, special effects, or cascades.
5. `max_clear_swap_label` samples a unique displayed arrow with the largest immediate clear count.
6. `target_clear_swap_label` samples a unique displayed arrow with the requested clear count.
