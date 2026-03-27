# Chart Domain Plan

## Purpose
Capture the chart types currently under consideration for `domain=charts` and the initial implementation scope we plan to build first.

This is a planning/source-of-truth note for chart-domain scope, not an active-task inventory yet.

## Taxonomy direction
1. Keep the same high-level split we use elsewhere: `domain -> task_group -> task -> task_variant`.
2. For charts, `task_group` should encode the reasoning family (for example `statistics`, `counting`, `comparison`), not the chart type.
3. Chart type should usually be a `scene_variant` inside a family/task, unless a later chart family truly needs a dedicated structural split.
4. One chart per image should remain the default starting point for the domain.

## Chart types under consideration

### High-priority first-class chart variants
These are the chart types we expect to support most naturally across multiple chart families.

1. `bar`
2. `horizontal_bar`
3. `grouped_bar`
4. `stacked_bar`
5. `line`
6. `area`
7. `multi_line`
8. `scatter`
9. `dot_plot`
10. `lollipop`
11. `radar`
12. `bubble`
13. `pie`
14. `donut`
15. `heatmap`

### Additional chart types we want to keep on the long-term consideration list
These are valid future targets, but they are not part of the initial implementation scope yet.

1. `area`
2. `stacked_area`
3. `box_plot`
4. `violin_plot`
5. `hexbin`
6. `density_contour`
7. `radar`
8. `treemap`
9. `waterfall`
10. `funnel`
11. `candlestick`
12. `gantt`

## Initial implementation target

The first implementation step is now active: `task_charts_statistics_summary_value`, `task_charts_statistics_summary_label`, `task_charts_counting_value_count`, `task_charts_readout_subset_value`, and `task_charts_multiseries_pairwise_comparison_count` under `domain=charts`.

The concrete v1 contract for the first rollout now lives in `CHART_TASK_SETUP.md`.

### First family
1. The first planned chart family is `statistics`.
2. This family should cover summary-value reasoning over the displayed data rather than chart-type-specific heuristics.
3. The first concrete tasks in that family are:
   - `task_charts_statistics_summary_value`
   - `task_charts_statistics_summary_label`
4. The numeric-summary task variants are:
   - `max`
   - `min`
   - `range`
   - `mean`
   - `median`
   - `sum`
   - `mode`
5. The label-answer companion task variants are:
   - `argmax`
   - `argmin`
   - `median_label`

### First chart variants to implement
These are the first chart variants we currently plan to support across the active chart tasks.

1. `bar`
2. `area`
3. `pie`
4. `donut`
5. `horizontal_bar`
6. `line`
7. `radar`
8. `scatter`
9. `dot_plot`
10. `lollipop`

Note:
1. `pie` and `donut` are composition-style chart variants: slices use distinct colors, the legend on the right maps colors to labels, and the numeric contract uses printed percentages rather than raw integer values.
2. Those pie-like variants should only be enabled on tasks whose semantics still make sense under percentage composition; they are not required for every active chart task.

### Chart variants we may add after the first statistics rollout stabilizes
1. `histogram`
2. `heatmap`

### Chart variants we are explicitly not planning for the first statistics rollout
These may still become later chart-family variants, but they are not part of the initial `statistics` implementation target.

1. `grouped_bar`
2. `stacked_bar`
3. `multi_line`
4. `bubble`
5. `box_plot`
6. `violin_plot`
7. `candlestick`
8. `treemap`

## Active and planned chart families
1. Active:
   - `statistics`
   - `counting`
   - `readout`
   - `multiseries`
2. Planned next:
   - `comparison`
   - `trend`
   - `spatial`
   - `relation`

## Notes
1. The chart-type universe above is intentionally broader than the first implementation target so we can return to it later without redoing discovery.
2. Family/task design should filter chart support selectively; we do not need every chart type to support every family.
3. When chart tasks land, update:
   - `docs/domains/TASK_FAMILY_VARIANTS.md`
   - `docs/project/STATUS.md`
   - `docs/project/TODO.md`
   - `docs/tasks/README.md`
