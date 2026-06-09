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
   - arithmetic-grid tasks should usually rise with row count, whether the hidden cell is an operand or a result, and whether the repeated row rule uses multiplication rather than simple addition.
   - paper-fold spatial tasks should usually rise with more marks, a higher fraction of marks that originate on the folded side, and option sets that contain stronger near-miss reflections.
   - cube-removal spatial tasks should usually rise with the original footprint size, total cube count, maximum height, removal count, and how many distinct columns changed between the left and right structures.
   - topology bead-loop tasks should usually rise with option count, bead count, how many valid options must be counted, and whether the identity depends on color only, shape only, or a mixed color+shape token.
   - cell-board tasks should usually rise with board area, obstacle/color-region count, path length or component count, and the size of the annotation set or path.
4. Use `scene_variant_load` only when the task genuinely supports multiple visible scene grammars inside the same task.
5. If a later puzzle family uses only one stable presentation, give `scene_variant_load` zero weight for that task/family instead of inventing fake variation.
6. Cell-board tasks should usually rise with board area, obstacle/color-region count, path length or component count, and the size of the annotation set or path.
