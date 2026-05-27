# Charts Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `reasoning_load`
- `scene_variant_load`

## Domain fallback weights
```yaml
visual_scan: 0.34
reasoning_load: 0.33
scene_variant_load: 0.33
```

## Scope notes
- Keep the chart-domain vocabulary broad. These three criteria should be scorable for every chart task.
- Let each task decide how to normalize its own raw knobs into these criteria.
- `scene_variant_load` should be task-dependent. Do not reuse one global chart-type difficulty table across unrelated chart tasks.
- Fixed-scene chart tasks may set `scene_variant_load` weight to `0.0` when the scene does not vary within the task; that is better than carrying a constant weighted criterion with no within-task ordering signal.
- Use task-group or task-level weight overrides only when a chart family really shifts the relative importance of scan, reasoning, and representation load.

## Notes
- Use chart-native structure in the score: mark count, category count, series count, or bin count for `visual_scan`, query semantics for `reasoning_load`, and task-local chart-type ordering for `scene_variant_load`.
- Chart tasks often get harder because of representation load and scene semantics, not because the final numeric answer is larger.

## Data Table Grid Notes
- `table` is a chart scene for row/column/cell data displays.
- Use the same broad chart vocabulary unless a task-group override is justified:
  - `visual_scan`: rows, numeric columns, filtered subset size, queried interval length, or ranking span the model must inspect.
  - `reasoning_load`: summary, transfer, ranking, filter, or interval logic required after reading the cells.
  - `scene_variant_load`: table styling or layout variation only when it creates real within-task representation load.
- Keep normalization task-local even when the criterion names are shared across table-grid tasks.
- Keep raw diagnostics such as row count, numeric-column count, selected-row count, and year-interval length in trace/debug payloads rather than in `complexity_components`.
