# `task_pages__infographic__filtered_section_extremum_label`

Status: accepted after qwen25vl7b solve-rate calibration.

## Taxonomy
1. Domain: `pages`
2. Scene id: `infographic`
3. Task id: `task_pages__infographic__filtered_section_extremum_label`
4. Implementation group: `pages/infographic`

## Contract
Filters infographic metric cards by one visible icon kind, sums the filtered
cards within each section, and asks which section has the highest or lowest
filtered total.

Query id: `section_icon_extremum_label`.

Answers are section-label strings. Evidence is a `bbox_set` over the
icon-filtered metric labels and printed values in the answer section.
