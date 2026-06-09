# TRACE Task Review Artifacts

Generated task-review artifacts belong here, grouped as:

```text
review/task-reviews/<domain>/<scene_id>/<task_id>/
```

The browser review app indexes this directory by default. The root starts empty
for a fresh review pass; do not copy stale generated artifacts from older
workspaces into this tree.

Operational notes:

- This tree contains generated review sidecars only. Reviewer comments, manual
  audit gates, feedback status, and agent repair notes live separately in
  `review/feedback/review_feedback.sqlite`.
- After regenerating anything in this tree, reload the browser review app index
  before inspecting or handing off.
- Resource review sheets belong under `review/task-reviews/assets/`; they are
  indexed through the app's Resources view and do not count as task samples.
- Do not manually edit generated sample JSON/images to address reviewer
  feedback. Fix code/config/prompts, regenerate the affected task review, reload
  the app, and add an agent repair note to the relevant feedback thread.
