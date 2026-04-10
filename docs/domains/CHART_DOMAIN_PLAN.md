# Chart Domain Plan

## Purpose
Capture the longer-horizon chart-domain direction for `domain=charts`.

This file is intentionally future-facing. It owns the broader chart-type universe and planning notes for later expansion. It is **not** the active chart contract. For currently supported chart families, tasks, and scene variants, use `docs/domains/CHART_TASK_SETUP.md`.

## Scope boundary
Use this file for:
- chart types we want to preserve on the long-term roadmap
- family-level taxonomy direction
- future expansion notes

Do **not** use this file as the source of truth for:
- active chart task inventory
- active chart-family coverage
- current scene-variant support

Those active details belong in `docs/domains/CHART_TASK_SETUP.md`, `docs/domains/TASK_FAMILY_VARIANTS.md`, and `docs/project/STATUS.md`.

## Taxonomy direction
1. Keep the normal TRACE split: `domain -> task_group -> task -> task_variant`.
2. In `charts`, `task_group` should encode the reasoning family (`statistics`, `counting`, `distribution`, `trend`, ...), not the chart type.
3. Chart type should usually remain a visual `scene_variant` inside a task unless the underlying scene grammar truly becomes a different grounding family.
4. One chart per image remains the default unless a family is explicitly multiseries or distribution-specific.

## Long-term chart-type universe

### First-class reusable chart variants
These are the chart types we expect to reuse naturally across multiple chart families over time.

1. `bar`
2. `horizontal_bar`
3. `grouped_bar`
4. `stacked_bar`
5. `stacked_horizontal_bar`
6. `line`
7. `area`
8. `multi_line`
9. `scatter`
10. `dot_plot`
11. `lollipop`
12. `radar`
13. `bubble`
14. `pie`
15. `donut`
16. `histogram`
17. `boxplot`
18. `violin`
19. `heatmap`

### Additional future chart types under consideration
These remain valid future targets, but they are not required for current chart coverage.

1. `stacked_area`
2. `ecdf`
3. `hexbin`
4. `density_contour`
5. `treemap`
6. `waterfall`
7. `funnel`
8. `candlestick`
9. `gantt`

## Family direction
1. Active chart reasoning families already live under:
   - `statistics`
   - `counting`
   - `readout`
   - `multiseries`
   - `distribution`
   - `composition`
   - `trend`
2. Likely future chart-family expansion still points toward:
   - `comparison`
   - `spatial`
   - `relation`

## Planning rules
1. Do not force every chart type onto every task; chart support should stay selective and semantics-driven.
2. When a chart type changes the perceptual contract but not the reasoning family, prefer widening `scene_variant` support inside the existing task before creating a near-duplicate task id.
3. If a proposed chart type requires a genuinely different scene grammar or witness contract, split helper placement first and task surface second.
4. If active chart support changes, update:
   - `docs/domains/CHART_TASK_SETUP.md`
   - `docs/domains/TASK_FAMILY_VARIANTS.md`
   - `docs/project/STATUS.md`
   - relevant task docs under `docs/tasks/`
