# Charts Coverage Extension

## Current Implementation Snapshot

This note tracks chart-domain coverage gaps after the 2026-05 chart expansion.
It should not list chart capabilities that are already covered by active default
tasks.

Current active chart-domain surface:

- Active default chart tasks: 100
- Active chart scenes: 33
- Public taxonomy: `charts -> scene_id -> task_id`

Implemented chart scenes:

- `area`
- `bar_3d`
- `boxplot`
- `candlestick`
- `combo_mark`
- `composition_chart`
- `curve_panels`
- `dashboard`
- `dumbbell`
- `error_interval`
- `heatmap`
- `histogram`
- `marker_map`
- `matrix`
- `multiseries`
- `parallel_coords`
- `part_whole`
- `pictogram`
- `radar`
- `radial_progress`
- `radial_sankey`
- `region_map`
- `sankey`
- `scatter_cluster`
- `scatter_readout`
- `single_series`
- `size_encoding`
- `small_multiple`
- `sunburst`
- `surface_3d`
- `table`
- `treemap`
- `violin`
- `waterfall`

The following earlier coverage gaps are no longer open chart gaps:

- Real geographic map visualization: covered by `region_map` and
  `marker_map`, with bundled synthetic maps plus geographic world,
  contiguous USA, EU, and China map assets.
- Bubble-on-map visualization: covered by `marker_map`.
- Error-bar and confidence-interval charts: covered by `error_interval`.
- Gauge and radial progress displays: covered by `radial_progress`.
- Waffle/pictogram quantity charts: covered by `pictogram`.
- Heatmaps and matrix grids: covered by `heatmap` and `matrix`.
- Treemap, sunburst, and composition hierarchy displays: covered by
  `treemap` and `sunburst`.
- Sankey and radial flow displays: covered by `sankey_flow` and
  `radial_sankey`.
- 3D charts: covered by `surface_3d` and `bar_3d`.
- Area, waterfall, candlestick, violin, radar, scatter, dumbbell, combo, and
  dashboard chart scenes: covered by their named active scenes.
- Table-like chart QA: covered by `table` in the public `charts` domain.

## Remaining Missing Chart Capabilities

### M0. Systematic Chart Rendering Variation Pass

Status: `active review requirement`

The chart domain now has broad chart-type coverage, but many scenes still share
a visually uniform house style: off-white canvas, white plot area, similar gray
axes, similar panel fills, and limited typography variation. This is a rendering
coverage gap rather than a new reasoning/task gap.

Scene-by-scene chart upgrades should consider:

- outer canvas/page background palettes beyond small off-white shifts;
- plot-area or chart-panel background tinting independent of the outer canvas;
- card/callout/surface fills for scenes that look like dashboards, reports, or
  embedded figures;
- axis, grid, tick, border, guide-line, title, and legend color variation;
- shared 30-family font sampling from `assets/fonts/`, using one family per
  meaningful text block;
- optional context/distractor text from `assets/context_text/` where it fits the
  scene contract;
- scene-specific readability fixes already reported during review, such as
  crowded legends, tiny labels, weak highlights, thin flow bands, label overlap,
  and overly uniform chart backgrounds.

Constraints:

- Treat this pass as render-only unless a scene-specific issue explicitly
  requires a semantic/config change.
- Protect semantic colors used for marks, series, heatmap scales, maps, legends,
  and answer-bearing categories.
- Preserve evidence bboxes and compute them after final style/layout.
- Keep all style choices seed-deterministic and independent of answer value,
  correct option, query id, and difficulty bucket.
- Generate scene review workbooks before running solve-rate calibration.

### M1. Controlled Unanswerable Chart Questions

Status: `missing`

TRACE chart tasks currently construct answerable instances with unique final
answers. ChartQA-style questions sometimes ask for a value, series, category,
panel, or time point that is not shown and expect an explicit unanswerable
answer.

Why this is still missing:

- No active chart task has an internal query branch whose correct final answer
  is `unanswerable`.
- No active chart verifier records a chart-specific proof of absence for a
  missing series/category/panel/x-value/metric.

Recommended first implementation:

- Add a narrow opt-in branch to lookup-style tasks only, not a broad global
  variant.
- Keep the public answer as the exact lowercase string `unanswerable`.
- Use empty `bbox_set` evidence for the unanswerable branch.
- Store the absence proof in metadata: requested missing item, visible candidate
  set, scope checked, and absence reason.

Good first candidates:

- `proposal:charts/scatter/series_point_lookup`: missing series or x value.
- `task_charts__dashboard__source_rank_target_value`: missing panel/source/category.
- `proposal:charts/table/statistics_column_summary_value`: missing column.
- `proposal:charts/trend/interval_change_value`: missing interval endpoint.
- `task_charts__heatmap__axis_cell_extremum_label`: missing row or column label.
- `task_charts__waterfall__running_total_value`: missing step label.

Avoid broad arithmetic/ranking/extremum tasks at first because the missing
entity can make the intended contract ambiguous.

### M2. Chart-Backed Page Context, Callouts, And Distractor Text

Status: `missing as a systematic chart capability`

Pages/infographic tasks cover page-layout reasoning, and dashboard charts cover
multi-panel chart layouts. The chart domain still lacks a systematic wrapper for
chart-backed context such as source notes, explanatory captions, footnotes,
callouts, decorative numbers, and irrelevant side text where the chart data
model remains the source of truth.

Why this is still missing:

- Current chart scenes are mostly self-contained chart renderers.
- Some scenes have visual style variation, but there is no universal chart
  context layer that records distractor/callout metadata and translates all
  chart/evidence bboxes through that wrapper.

Recommended implementation:

- Add a reusable chart context wrapper that can place a rendered chart into
  report/news/academic/infographic-style framing.
- Record context text, distractor text, source notes, callout ids, style id, and
  layout id in `render_spec`.
- Ensure distractors never introduce another valid answer.
- Apply only after scene review, because this can easily reduce readability.

Boundary:

- Keep this in `charts` only when the chart data model is the semantic source
  of truth.
- If the page layout itself is the semantic source of truth, keep it in `pages`.

### M3. Axis, Tick, Unit, And Scale Stressors

Status: `missing / partial only`

Many benchmark failures involve reading a chart with nonstandard axis or unit
presentation rather than a missing reasoning operation.

Currently covered:

- Many chart scenes support value windows, nonzero axis starts, guides, exact
  labels, and style variation.

Still missing as explicit calibrated capabilities:

- irregular tick spacing;
- dense date/time axes;
- rotated or abbreviated axis labels as a first-class stressor;
- mixed units or unit conversion stated in the chart;
- log or broken axes;
- nearest-tick / interpolation questions;
- charts where exact values must be inferred from a scale instead of printed
  value labels or guide lines.

Recommended implementation:

- Add these only to scenes where the evidence and verifier contract remain
  unambiguous.
- Start with one lookup/readout-heavy scene, not all charts.
- Treat them as render/query knobs with clear calibration gates, because they
  can make exact visual readout too hard quickly.

### M4. Parallel Coordinates And Multi-Axis Profile Charts

Status: `implemented in active chart taxonomy`

TRACE now includes the `parallel_coordinates_profile` scene, where each item is
a labeled polyline crossing several vertical metric axes.

Why this is still missing:

- Radar profiles compare values around a polar metric layout.
- Multiseries charts compare series over categories or x-values.
- Neither captures axis-to-axis crossing/order reasoning in a parallel
  coordinates scene.

Implemented task contracts:

- count profiles satisfying threshold conditions across two specified axes;
- find the profile with the largest increase, decrease, or absolute change
  between two axes;
- count line crossings between adjacent axes, either globally or involving a
  named profile.

Implementation guidance:

- Use modest item/axis counts.
- Use direct labels or a compact legend to avoid impossible line tracking.
- Evidence should be the polyline or axis-adjacent segment(s) used.

## Not Counted As Current Chart Gaps

The following benchmark patterns are intentionally not prioritized as missing
chart-domain capabilities:

- Multi-answer/list outputs. TRACE prefers single typed final answers; map these
  to count, extremum, ranking, or one selected label where possible.
- Pure graph/network reasoning appearing inside chart benchmarks. Route to the
  `graph` domain unless the visual is a quantitative chart such as sankey or
  radial sankey.
- Pure flowchart/process reasoning. Route to `pages/process_flow`.
- Clock-face reading/comparison. Route to puzzle clock tasks.
- Gantt, schedule, calendar, and milestone-timeline reasoning. Route to
  `pages` schedule/calendar/timeline scenes.
- Generic chart element localization as the final answer. Chart tasks already
  provide grounding as evidence; add a new task only when localization itself
  adds a distinct reasoning contract.

## Cross-Domain Boundary Notes

- The boundary between `charts` and `pages/infographic` is case-by-case.
- If the chart data model is the primary semantic source of truth, keep the task
  in `charts` even if the renderer adds page-like context, captions, callouts,
  or surrounding explanatory text.
- If the page layout, document sections, cards, controls, form fields, or
  multi-region document structure are the primary semantic source of truth, keep
  the task in `pages`.
- If a benchmark example mixes charts and pages in a way that suggests a new
  scene, decide the owning domain by the verifier metadata contract rather than
  by the visual style alone.
