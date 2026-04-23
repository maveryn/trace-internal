# Plans Progress

This file tracks short status notes for active or blocked planning work that should be easy to scan without opening the full task records.

## Current Status

### task_charts_composition_subset_value

- domain: `charts`
- status: `blocked`
- calibration model: `Qwen/Qwen3-VL-8B-Instruct`
- current verdict: not suitable for inclusion in its current form

Brief summary:
- the old task was retired because it was dominated by trivial printed-value lookup
- the task was redesigned into a stacked-only composition-arithmetic task and reevaluated with fresh `200 x 32` probes
- the redesigned task is still not calibrated:
  - `category_subset_sum` remains overwhelmingly too easy
  - `series_across_categories_sum` improves only slightly with larger charts and is still too easy
  - `subset_margin_sum` is the only variant with meaningful mixed-signal behavior, but it is unstable and highly sensitive to support changes

What would be needed to keep it:
- redesign the first two variants so both require stronger two-axis reasoning, not mostly local summation
- keep the family stacked-only and avoid reintroducing pie/donut scenes
- keep overlap guards against duplicating other chart tasks
- rerun the full `200 x 32` calibration loop after the semantic redesign

If we do not want another semantic redesign pass:
- drop this task from the calibration set and move on

Detailed record:
- [charts/task_charts_composition_subset_value.md](difficulty_calibration/charts/task_charts_composition_subset_value.md)
