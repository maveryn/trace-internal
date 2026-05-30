# `task_charts__dashboard__top_k_overlap_count`

## Contract
1. Domain: `charts`
2. Scene id: `dashboard`
3. Source implementation domain/group: `charts/dashboard`
4. Query id: `top_k_overlap_count`
5. The task counts shared category labels between two ranked top-k panel sets.

## Implementation
1. Registered class: `trace.tasks.charts.dashboard.cross_panel_query.ChartsDashboardTopKOverlapCountTask`
2. Prompt lookup domain/group: `charts/dashboard`
3. Generation is deterministic for the same seed, params, and task versions.
4. Answers and evidence are verifier-backed by trace metadata, not image pixels.
