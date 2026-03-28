# Tables Complexity

## Current status
- Table complexity rollout is still pending.
- Active table tasks still use legacy ad hoc `complexity_score` formulas, so this file should guide the eventual migration rather than describe current emitted criteria.

## Recommended criteria vocabulary
- `visual_scan`
- `reasoning_load`
- `output_burden`

These criteria are broad enough to apply across the current single-table suite:
- `visual_scan`: rows, numeric columns, filtered subset size, queried interval length, or ranking span the model must inspect.
- `reasoning_load`: summary/transfer/ranking/filter logic required after reading the cells.
- `output_burden`: how much ordered evidence or multi-cell witness structure the task requires the model to return.

## Suggested domain fallback weights
```yaml
visual_scan: 0.40
reasoning_load: 0.45
output_burden: 0.15
```

## Task-family notes
- `statistics`: keep `reasoning_load` highest; filtered statistics can raise `output_burden` because they return ordered `[filter cell, target cell]` witnesses.
- `counting`: let `visual_scan` grow with row count and matching-row coverage; pairwise column-count variants should also raise `output_burden` because each witness row contributes two boxes.
- `readout`: keep `reasoning_load` modest, but raise `output_burden` for two-cell arithmetic versus one-cell lookup.
- `relation`: transfer and comparison tasks are usually moderate `reasoning_load`; transfer variants also have explicit ordered two-cell witnesses.
- `ranking`: increase `reasoning_load` with larger rank depth and preserve non-trivial `visual_scan` because the witness is the full queried column ordering.
- `temporal`: let `visual_scan` grow with year-span length and let `reasoning_load` reflect lookup vs delta vs interval summary.

## Notes
- Keep normalization task-local even if the criterion names are domain-wide.
- Do not revive older `row_scan` / `column_scan` / `filter_reasoning` vocab unless the domain genuinely needs that extra granularity across every table task.
- Keep raw diagnostics such as row count, numeric-column count, selected-row count, and year-interval length in trace/debug payloads rather than in `complexity_components`.
