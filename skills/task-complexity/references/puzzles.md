# Puzzles Complexity

Use a small shared vocabulary for puzzle tasks unless a broader family proves it needs more:

- `visual_scan`
- `reasoning_load`
- `scene_variant_load`

Guidance:
1. Keep complexity within-task only. Do not compare puzzle scores against other domains.
2. For arithmetic unknown-slot puzzles, `visual_scan` should usually come from the visible slot count or operand count.
3. Keep `reasoning_load` task-local and variant-local:
   - result-unknown equations are easier,
   - operand-unknown equations are harder,
   - more operands, more operator variety, and the presence of multiplication can increase difficulty inside the same task.
   - balance-panel tasks should usually rise with panel count, total box count, and how many symbolic values must be chained before the query box can be solved.
4. Use `scene_variant_load` only when the task genuinely supports multiple visible scene grammars inside the same task.
5. If a later puzzle family uses only one stable presentation, give `scene_variant_load` zero weight for that task/family instead of inventing fake variation.
