# `task_pages__infographic__section_rank_label`

## Taxonomy
1. Domain: `pages`
2. Scene id: `infographic`
3. Task id: `task_pages__infographic__section_rank_label`
4. Implementation group: `pages/infographic`

## Contract
Selects an infographic section label by comparing aggregate section totals.

Query ids: `section_ranked_total_label|section_icon_extremum_label`.

Answers are exact section-label strings. Evidence is a `keyed_bbox_map` over the supporting metric-card boxes in the answer section, keyed by their visible metric-card labels.
