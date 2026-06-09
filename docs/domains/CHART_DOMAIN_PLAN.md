# Chart Domain Plan

## Purpose
Capture the longer-horizon chart-domain direction for `domain=charts`.

This file is intentionally future-facing. It owns the broader chart-type universe and planning notes for later expansion. It is **not** the active chart contract. For currently supported chart scenes, tasks, and query branches, use `docs/domains/CHART_TASK_SETUP.md`.

## Scope boundary
Use this file for:
- chart types we want to preserve on the long-term roadmap
- scene-level taxonomy direction
- future expansion notes

Do **not** use this file as the source of truth for:
- active chart task inventory
- active chart-scene coverage
- current query/render support

Those active details belong in `docs/domains/CHART_TASK_SETUP.md` and `docs/project/STATUS.md`.

## Taxonomy direction
1. Keep the public TRACE split: `domain -> scene_id -> task_id`.
2. Public `task_id` is the default sampling unit. Mirror directions, threshold sides, rank choices, and other branches of the same objective should stay inside `query_id`.
3. Chart type can be an internal render axis when the scene grammar and annotation contract stay the same. When the visual grammar changes materially, use a separate `scene_id`.
4. `task_group` remains only a source module/config grouping layer and should not drive public task enumeration.

## Long-term chart-type universe

### First-class reusable chart render forms
These are the chart render forms we expect to reuse naturally across multiple chart scenes over time.

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
20. `candlestick`

### Additional future chart types under consideration
These remain valid future targets, but they are not required for current chart coverage.

1. `stacked_area`
2. `ecdf`
3. `hexbin`
4. `density_contour`
5. `treemap`
6. `waterfall`
7. `funnel`
8. `gantt`

## Scene Direction
1. Active chart work is organized by public scenes such as `single_series`, `part_whole`, `table`, `dashboard`, `curve_panels`, `heatmap`, `sankey`, and `region_map`.
2. Likely future chart expansion should first add tasks to existing scenes when the scene grammar already fits.
3. Add a new scene only when Vero-style coverage requires a genuinely new visual grammar or annotation contract, such as chart/table combo figures or callout-annotation panels.

## Planning rules
1. Do not force every chart type onto every task; chart support should stay selective and semantics-driven.
2. When a chart render form changes appearance but not the scene grammar, prefer a render/query parameter inside the existing scene before creating a near-duplicate task id.
3. If a proposed chart type requires a genuinely different scene grammar or witness contract, split helper placement first and task surface second.
4. If active chart support changes, update:
   - `docs/domains/CHART_TASK_SETUP.md`
   - `docs/project/STATUS.md`
   - relevant task docs under `docs/tasks/`
