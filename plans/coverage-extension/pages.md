# Pages Coverage Extension

## Scope

This note tracks page-domain coverage gaps found from the external benchmark
failure analysis, then records candidate changes for `pages`.

Current working conclusion: the pages domain already covers many structured
document, infographic, form, GUI, web, process-flow, schema, calendar, schedule,
timeline, concept-map, and map reasoning contracts. The main gaps are denser
page styling, richer OCR-light layouts, broader desktop/app screen variants,
and a few case-by-case scene wrappers for chart/graph/process-flow content
inside infographic-like pages.

Boundary rule:

- Handle `charts` vs `pages/infographic` case by case.
- Put a task in `charts` when chart data is the primary verifier source of
  truth.
- Put a task in `pages` when page layout, document sections, cards, controls,
  form fields, or multi-region document structure are the primary verifier
  source of truth.
- Decide new mixed scenes by the verifier metadata contract, not by visual style
  alone.

## Identified Issues

### P1. Dense OCR-Light Infographic And Document Pages

Status: `partial`

InfoVQA failures include OCR span lookup, filtered counts, table/list lookup,
and non-extractive synthesis across multiple text regions. TRACE has structured
page tasks, but current scenes are cleaner and shorter than many real
infographics.

Closest existing tasks:

- `task_pages__infographic__metric_arithmetic_value`
- `task_pages__infographic__filtered_metric_total_value`
- `task_pages__infographic__section_ranked_total_label`
- `proposal:pages/counting/filter_count`
- `proposal:pages/arithmetic/section_expression_value`
- `proposal:pages/cross/form_reconciliation_value`
- `proposal:charts/table/counting_value_predicate_count`
- `proposal:charts/table/statistics_column_summary_value`

Interpretation:

- This is mostly a scene/rendering density gap, not a need for broad free-form
  OCR QA.
- Keep pages OCR-light: short visible labels, field values, section headers,
  and controlled spans.
- Avoid long paragraphs, open-domain named-entity lookup, and answers requiring
  world knowledge.

### P2. Document Table, List, And Card Lookup Variety

Status: `partial`

Benchmark examples often ask for values from dense lists, ranked tables,
profile cards, timelines, or mixed table-card layouts.

Closest existing tasks:

- `proposal:pages/counting/filter_count`
- `task_pages__infographic__filtered_metric_total_value`
- `task_pages__infographic__filtered_section_extremum_label`
- `task_pages__infographic__column_profile_comparison_value`
- `proposal:charts/table/ranking_kth_rank_in_column_label`
- `task_charts__table__temporal_row_interval_difference_value`

Interpretation:

- The reasoning contracts exist, but the page scene space should support more
  table/list/card hybrids.
- This should stay single-answer: count, extremum label, ranked label, lookup
  value, or arithmetic value.

### P3. Non-Extractive Synthesis From Multiple Visible Regions

Status: `partial`

Some InfoVQA failures require combining multiple visible fields, such as
comparing form values, summing section totals, or deriving one short answer from
several text/value regions.

Closest existing tasks:

- `proposal:pages/cross/form_reconciliation_value`
- `proposal:pages/arithmetic/section_expression_value`
- `task_pages__infographic__metric_arithmetic_value`
- `task_pages__infographic__column_profile_comparison_value`

Interpretation:

- TRACE already has this pattern in a few page tasks.
- Add coverage by extending scene variety and adding controlled query branches,
  not by adding free-form synthesis.

### P4. Desktop/App GUI Targeting And Chrome Variety

Status: `partial / eval caveat`

ScreenSpotPro failures are dominated by GUI target grounding, but that run has
a coordinate-scaling caveat. TRACE pages already include GUI/web relation tasks
that return option labels with bbox evidence, not absolute point answers.

Closest existing tasks:

- `proposal:pages/relation/command_intent_target_label`
- `proposal:pages/relation/navigation_path_target_label`
- `proposal:pages/relation/professional_target_label`
- `proposal:pages/relation/web_action_target_label`
- `proposal:pages/counting/filter_count`

Interpretation:

- Do not overreact to ScreenSpotPro score until the eval setup is corrected.
- The useful TRACE extension is richer synthetic desktop/app chrome and control
  idioms, while keeping answer labels and bbox evidence.
- Absolute point-output GUI grounding is not a priority unless we explicitly
  decide to add point-answer style tasks.

### P5. Infographic-Style Graph, Network, And Process-Flow Pages

Status: `partial`

ChartMuseum and InfoVQA include graph/network/flowchart traversal inside
infographic pages. TRACE has graph tasks and process-flow page tasks, but the
visual presentation is usually cleaner than real infographic layouts.

Closest existing tasks:

- `proposal:pages/process/flow_condition_path_endpoint_label`
- `proposal:pages/process/flow_filtered_node_count`
- `proposal:pages/process/flow_actor_handoff_count`
- `proposal:graph/relation/common_neighbor_count`
- `proposal:graph/path/shortest_path_length`

Interpretation:

- Process-flow semantics belong in `pages/process_flow`.
- Graph-theory semantics belong in `graph/node_link_graph`.
- Page-style wrappers or infographic visual variants can be added case by case
  around either family, but the owning domain should follow the verifier
  metadata contract.

### P6. Multi-Span Or List Answers

Status: `out of scope`

InfoVQA includes questions with multiple answer spans. TRACE should keep the
same design stance as charts: do not add page tasks whose final answer is a list
or unordered set.

Interpretation:

- Map benchmark-style multi-span questions to single-answer contracts where
  possible: count, extremum, ranked label, selected label, or derived value.
- Avoid new `string_list` or unordered-set answer types for this coverage wave.

### P7. Open Visual Knowledge And Entity/Fact Lookup

Status: `out of scope`

SimpleVQAEn failures include person identity, public facts, locations, awards,
and other knowledge-heavy questions not visibly grounded in the image.

Interpretation:

- Keep these out of TRACE unless the relevant fact is rendered as visible text
  or represented in controlled synthetic metadata.
- Do not add broad OCR/document QA that depends on real-world entity knowledge.

## Planned Changes

### Q1. Add Denser OCR-Light Page And Infographic Scene Variants

Decision: candidate.

Issues addressed:

- P1. Dense OCR-light infographic and document pages.
- P2. Document table, list, and card lookup variety.
- P3. Non-extractive synthesis from multiple visible regions.

Implementation idea:

- Extend `infographic`, structured document sections, and GUI table/list
  scenes with denser but controlled layouts.
- Add profile-card grids, ranked lists, compact statistic panels, source notes,
  sidebars, footnotes, section subtitles, and controlled distractor text.
- Keep all answer-bearing text short and trace-generated.
- Record distractor text, section ids, field ids, and bbox maps in trace
  metadata.

### Q2. Add Desktop/App Chrome Style Packs For GUI Page Tasks

Decision: candidate.

Issues addressed:

- P4. Desktop/app GUI targeting and chrome variety.

Implementation idea:

- Broaden GUI scene variants for `office_document`, `creative_workspace`,
  `developer_ide`, `cad_workspace`, `scientific_plotter`, and
  `os_file_manager`.
- Add ribbon/menu/dialog/palette/sidebar/property-panel style packs.
- Keep answer as option label and evidence as ordered `bbox_set` over guide,
  context, header, and control boxes.
- Revisit absolute point-output only after ScreenSpotPro coordinate evaluation
  is fixed and if point-output tasks become a deliberate target.

### Q3. Add Infographic Wrappers For Process-Flow And Graph-Like Pages Case By Case

Decision: candidate.

Issues addressed:

- P5. Infographic-style graph, network, and process-flow pages.

Implementation idea:

- For process-flow semantics, add page-style process-flow variants under
  `pages/process_flow`.
- For graph-theory semantics, prefer graph-domain tasks with optional
  infographic-style rendering wrappers.
- Keep ownership based on verifier metadata: workflow/status/lane/decision
  metadata goes to `pages`; graph adjacency/path/degree metadata goes to
  `graph`.

## Remaining Open Questions

These are intentionally left undecided until we discuss them.

1. Which pages change should be first: denser infographic/document pages, GUI
   chrome style packs, or process-flow/graph infographic wrappers?
2. Should any pages tasks get a narrow `unanswerable` branch like the selected
   chart tasks, or should unanswerable stay chart-only for now?
