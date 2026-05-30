# `task_games__match3__swap_effect_value`

## Contract
1. Domain: `games`
2. Task group: `match3`
3. Scene id: `match3`
4. Query ids: `cleared_count_after_marked_swap`, `created_run_count_after_marked_swap`
5. Objective: compute a numeric immediate effect of the marked adjacent match-3 swap.
6. Answer type: `integer`.
7. Evidence type: `point_set` over the affected gems or created-run centers.

## Generation Notes
1. The scene shows a match-3 board with row/column numbers, colored gems, and one marked adjacent-swap arrow.
2. The board has no matching runs before the marked swap.
3. The rule applies one adjacent swap, then clears every horizontal or vertical run of at least three matching gems.
4. The task does not apply gravity, refill, special effects, or cascades.
5. `cleared_count_after_marked_swap` counts the unique gems cleared immediately; evidence contains one point at each cleared gem center, or `[]` for zero.
6. `created_run_count_after_marked_swap` counts the horizontal or vertical matching runs created immediately; evidence contains one point near each run center, or `[]` for zero.
7. Rendering uses shared game panel styles, sampled fonts, and five scene-local gem/board styles.
