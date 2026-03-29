# Temporal Complexity

## Recommended criteria vocabulary
- `visual_scan`
- `ambiguity`
- `clutter`

## Domain fallback weights
```yaml
visual_scan: 0.40
ambiguity: 0.35
clutter: 0.25
```

## Task-group overrides

### `clock`
```yaml
time_reading: 0.55
visual_scan: 0.20
ambiguity: 0.15
clutter: 0.10
```

Measure:
- minute-grid difficulty and hand-angle separation,
- whether the query asks for direct readout or an offset transform,
- scene-variant readability differences such as fuller ticks vs cleaner chrome,
- any readability pressure from closely spaced hands or heavier scene chrome.

### `calendar`
```yaml
calendar_lookup: 0.55
visual_scan: 0.20
ambiguity: 0.15
clutter: 0.10
```

Measure:
- whether the query asks for nth-weekday lookup, marked-weekend counting, or a day-gap computation,
- how many calendar rows and marked dates the instance exposes,
- whether the sought date is later in the month or the marked-day set is denser,
- scene-style readability differences such as fuller header/grid chrome vs lighter minimal layouts.

### `schedule`
```yaml
interval_reasoning: 0.55
visual_scan: 0.20
ambiguity: 0.15
clutter: 0.10
```

Measure:
- whether the query asks for overlap reasoning, duration comparison, or a unique optimization over non-overlapping events,
- how many event blocks and planner lanes the instance exposes,
- whether near-touching boundaries or near-equal event durations make the target set harder to separate,
- scene-style readability differences such as fuller grid/header chrome vs lighter minimal layouts.

## Notes
- Keep temporal-domain criteria broad at domain scope; clock-specific `time_reading` belongs at task-group scope unless later temporal families all need the same notion.
- Calendar-specific `calendar_lookup` likewise belongs at task-group scope; do not promote it to domain level unless later temporal families share the same lookup semantics.
- Schedule-specific `interval_reasoning` likewise belongs at task-group scope; keep it there unless later temporal families truly share the same interval-selection semantics.
- For offset variants, let the task-local normalized `time_reading` value absorb the extra mental step; do not encode that shift as a separate task-local weight fork.
- If a later temporal family uses a single stable presentation with negligible clutter variation, prefer zero weight on `clutter` over carrying a constant non-signal criterion.
