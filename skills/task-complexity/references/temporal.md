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

## Notes
- Keep temporal-domain criteria broad at domain scope; clock-specific `time_reading` belongs at task-group scope unless later temporal families all need the same notion.
- For offset variants, let the task-local normalized `time_reading` value absorb the extra mental step; do not encode that shift as a separate task-local weight fork.
- If a later temporal family uses a single stable presentation with negligible clutter variation, prefer zero weight on `clutter` over carrying a constant non-signal criterion.
