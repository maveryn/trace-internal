# Pages Complexity

Use a small shared vocabulary for pages tasks unless a task group needs a justified override:

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
- Keep complexity within-task only. Do not compare page scores against other domains.
- Use `visual_scan` for visible field count, node count, event count, control count, schema-field count, page density, or local search burden.
- Use `reasoning_load` for arithmetic, matching, filtering, order, interval, path, hierarchy, process-flow, schema-role, or GUI-command reasoning.
- Use `scene_variant_load` only when the task genuinely supports multiple visual grammars with different search burden.
- Normalize each criterion inside the task before combining it, and keep the weighted aggregate inside `[0, 1]`.

## Task-Group Notes
- Arithmetic and cross-form pages: `visual_scan` rises with section/row/field count; `reasoning_load` follows the arithmetic or reconciliation operation.
- Cycle and hierarchy pages: `visual_scan` rises with stage/node count and depth; `reasoning_load` follows offsets, subtree burden, or path burden.
- Calendar, schedule, and timeline pages: `visual_scan` rises with date, event, or milestone density; `reasoning_load` follows weekday lookup, marked-day counting, overlap, optimization, duration comparison, or interval membership.
- Infographic pages: `visual_scan` rises with section, card, and metric count; `reasoning_load` follows the selected filter, ranking, aggregate, or extrema operation.
- Concept-map, process-flow, and schema pages: `visual_scan` rises with node/step/field/relationship count; `reasoning_load` follows role filters, branch order, conditional paths, handoffs, cardinality, or role semantics.
- GUI-like pages: `visual_scan` rises with visible control/row/guide count; `reasoning_load` follows command mapping, path following, or control-state filtering.
