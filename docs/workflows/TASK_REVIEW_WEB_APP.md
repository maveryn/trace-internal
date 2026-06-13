# Task Review Web App

The task-review web app is the browser replacement for workbook-first manual
inspection. It reads the active review sidecars under `review/task-reviews` and
persists reviewer issue threads in a separate SQLite database. The reviewer UI
uses **issue/issues** for actionable human comments, and browser-facing issue
pages live under `/issues`. Internal API names, CSS hooks, and SQLite tables
still use `feedback` for compatibility.

## Default Review Workflow

For new tasks, renderer changes, prompt changes, or distribution-changing
logic, generate the normal task-review sidecars, then review them in the app:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

Then use this review loop:

1. For scene-package migration scenes, generate review artifacts only after
   `manual_code_audit_status.json` exists for the scene and has `passed: true`.
   This file records the agent-side manual source audit for role boundaries and
   the app shows it as the scene-level code audit status.
   Scene-package migration also requires `taxonomy_review_status.json` for the
   scene with `passed: true`; the app shows it as the scene-level taxonomy
   audit status.
2. Generate review artifacts under `review/task-reviews` as usual.
3. If one scene under `review/task-reviews` changed, prefer the scene-scoped
   reload API, `POST /api/reload/scene/<domain>/<scene_id>`. If many scenes or
   shared review assets changed, click **Reload Index** in the app or call
   `POST /api/reload`. Reload runs in the background; the app keeps serving the
   previous index until the rebuild finishes and swaps in.
4. Inspect through the browser app by domain, scene, task, and query id.
5. Use scene, task, and sample pages to review image, prompt, answer, annotation,
   distribution status, review status, and solve-rate status.
6. Save sample-specific issues in the app so comments are keyed to the exact
   sample identity; do not use Excel notes as the default issue channel.
7. Mark the review checkboxes only after prompt, image, annotation,
   distribution, code review, and taxonomy review are acceptable. This is the
   non-solve-rate review completion status shown in domain and scene views.
8. Mark the solve-rate checkbox separately after solve-rate artifacts have been
   inspected. Domain and scene views show solve-rate completion separately
   because solve-rate review often happens after visual/manual review.
9. Use Excel workbooks only as optional static exports for archival, sharing
   outside the app, or fallback debugging.
10. If web-app code, templates, CSS, JavaScript, indexer logic, resource
   indexing, feedback storage, or schemas changed, restart the app instead of
   only reloading the index.
10. After reload or restart, verify the affected domain/scene/task/sample page
    shows the updated local files, statuses, and issue controls before
    handing off.
11. When an agent fixes a reviewer issue, add an agent repair note to the
    existing issue thread after validation. The repair note is the handoff
    from agent to reviewer; it is not the resolution.
12. Reviewer/human resolution changes the underlying feedback status to
    `resolved`. Resolved issues leave the open work queue but remain stored,
    exportable, and inspectable through their thread/detail page.

Excel workbooks are no longer the required manual-inspection surface. They are
kept only as optional static exports for archival, sharing outside the app, or
fallback debugging. Do not block a review solely because an `.xlsx` file is
missing when the JSON/image sidecars and manifests are current and visible in
the app.

## Run

Local-only access:

```bash
PYTHONPATH=. python scripts/run_review_app.py --host 127.0.0.1 --port 7860
```

The launcher emits browser-facing links under `/proxy/{port}` by default, so
the same process works through Jupyter Server Proxy. For root-relative
localhost-only links during debugging, pass `--base-url ''` explicitly.

Remote access:

```bash
export TRACE_REVIEW_APP_TOKEN='<shared-review-token>'
PYTHONPATH=. python scripts/run_review_app.py --host 0.0.0.0 --port 7860
```

The launcher refuses to bind a non-localhost host without a token. The app uses
one shared token and an HttpOnly cookie after login. Static media and overlays
are served only for indexed review artifacts, not arbitrary filesystem paths.

When running inside Jupyter, open the app through the server-proxy URL:

```text
http://<host>:8888/proxy/7860/
```

If Jupyter asks for its own login, authenticate to Jupyter first, then open the
proxy URL and enter `TRACE_REVIEW_APP_TOKEN` at the TRACE Review login screen.

## Refresh Rules

Agents must refresh the app before reporting that regenerated review artifacts
are ready:

- If one scene under `review/task-reviews` changes, prefer
  `POST /api/reload/scene/<domain>/<scene_id>` before inspecting or handing off
  the app URL. This rebuilds only that scene in the index and swaps it into the
  current in-memory index.
- If many scenes changed, or files under `review/task-reviews/assets` changed,
  click **Reload Index** or call `POST /api/reload`. This starts a full
  background index rebuild and returns immediately; poll
  `GET /api/reload/status` or wait for the browser to refresh after the new
  index is installed. Refreshing includes task samples, images, `data/*.json`,
  manifests, distribution files, solve-rate artifacts, and scene review
  manifests.
- The app shows a `Review artifacts changed` banner when files under
  `review/task-reviews` are newer than the loaded index. Treat that banner as a
  blocker for visual inspection until **Reload Index** has completed
  successfully.
- If review-app code changes, restart the server. This includes templates,
  CSS/JS, server routes, indexer logic, resource indexing, feedback storage, and
  schema changes. The launcher binds the server before the first full index scan
  finishes; if the app shows an index-loading notice, wait for the background
  reload to complete before reviewing regenerated samples.
- After either refresh path, open the affected domain/scene/task/sample page and
  verify the displayed image/prompt/annotation/status reflects the local files.
- Issue comments, manual audit checkboxes, theme changes, and ordinary
  navigation do not require **Reload Index**.

## Data Sources

The app scans:

- `review/task-reviews/<domain>/<scene_id>/scene_review_manifest.json`
- `review/task-reviews/<domain>/<scene_id>/<task_id>/manifest.json`
- `distribution_review.json` and `random_review_100.json` when present
- `data/<query_id>/*.json`
- `images/<query_id>/*.png`
- `docs/tasks/<task_id>.md` for the condensed task-page taxonomy summary:
  domain, scene id, query ids, answer schema, annotation schema, and program
  contract. If the task doc is missing, the app falls back to indexed sample
  query ids and observed answer/annotation schemas.

Domain discovery is registry-driven: only public active domains listed in
`trace.core.taxonomy.ACTIVE_DOMAINS` are eligible for task-review indexing.
Folders under `review/task-reviews` that are not active domains, including
`review/task-reviews/assets`, are reserved for separate resource review surfaces
and do not affect domain, scene, task, sample, or default search counts.

The separate **Resources** link opens `/resources`, which scans
`review/task-reviews/assets` for review-only images and JSON manifests such as
font contact sheets, icon sheets, illustration object sheets, 3D object inventory
sheets, and other support assets. Resource files are served only through stable indexed ids under
`/resources/media/<asset_id>`; they are not task samples and do not use sample
issue threads.

The separate **3D Objects** link opens `/three-d/objects`, which renders one
lazy-loaded native preview per canonical `three_d` object profile. The page is
grouped by the object profile family (`object_scene`, `object_cluster`, room
wall/floor, street, and warehouse) and persists profile-level decisions in the
same review SQLite DB. Use **Approve**, **Remove**, or **Improve rendering**
with a note when auditing object fidelity. These decisions are keyed by
`profile_id` from `trace/tasks/three_d/shared/object_resources.py`; they are not
sample-specific issue threads and do not affect task-review completion gates.
Export the saved decisions through `/api/three-d/objects/reviews/export.jsonl`
when turning object-review notes into implementation work.

The separate **Illustration Objects** link opens `/illustrations/objects`,
which renders one lazy-loaded preview per reusable illustration object/style
entry. The page has renderer tabs for `vector`, `top_down_pixel_rpg`, and
`isometric_pixel_rpg`, plus category tabs for object families such as people,
plants, fixtures, structures, vehicles, and objects. It pulls vector entries
from the shared illustration object catalog/library and pixel RPG entries from
the shared top-down/isometric object dispatcher, so newly registered reusable
objects appear without committing new preview PNGs. Use **Approve**, **Remove**,
or **Improve rendering** with a note when auditing illustration object fidelity.
The summary counts and decision tabs filter the page by saved decision; use the
**Improve** filter to view the current rendering issue list for the selected
renderer/category.
These decisions are keyed by renderer-specific `item_id` values and stored in
`illustration_object_review`; they are not sample-specific issue threads and do
not affect task-review completion gates. Export the saved decisions through
`/api/illustrations/objects/reviews/export.jsonl`.

Scene pages link to `/domains/<domain>/scenes/<scene_id>/review`, a scene-level
review surface that shows two preview slots for every query id under every task
in the scene. The number of image cards is therefore `query_count * 2`, with a
missing-sample placeholder shown when a query has fewer than two indexed review
samples. Use this page to inspect scene-wide rendering or prompt patterns in one
scrolling pass. Scene-level issues filed there are stored with an empty
`task_id`, link back to the scene review page, and should be used only for
feedback that applies across the scene family rather than to one task or one
exact generated sample.

The separate **Taxonomy** link opens `/taxonomy`, which browses the current
taxonomy audit artifacts under `review/taxonomy-audit`. The taxonomy browser is
for task-boundary review, not generated task completion. It shows current task
and query ids mapped to proposed task ids, attaches available current review
samples for each query, and links back to the normal task/sample pages for
image, prompt, answer, and annotation inspection. The taxonomy overview shows
global decision-review progress as approved decisions over total current tasks,
plus the number of current tasks with open taxonomy issues. Each taxonomy task
detail page has an **Approve Decision** control for accepting the proposed
keep/split/rename mapping. If the decision is not acceptable, file a taxonomy
issue from that page; filing a taxonomy issue automatically clears approval for
that taxonomy task. Use **Next Pending**, **Approve and Next**, or **Save Issue
and Next** to advance through the remaining pending taxonomy items in the same
domain queue. Taxonomy decision approvals are stored in the same review
SQLite database in `taxonomy_decision_review`; taxonomy issues remain in the
normal feedback tables with the `[taxonomy:<round>]` prefix. Taxonomy task
pages also show **Arguments / Variant Axes** from `program_arguments_json`.
These rows explain allowed in-task argument values for review; `needs_review`
means the builder could only infer a weak/default argument description and a
manual override may be useful.
`/taxonomy/contract-v0/tree` shows the proposed units as a
contract-v0 program tree:
`domain -> program root -> program signature -> proposed task unit`, with each
unit also showing its base program contract when the exact task-level contract
is narrower than the signature family. Taxonomy comments are stored in the
normal issue database as task-level issues with a
`[taxonomy:<round>]` prefix, so they remain visible in task issue history and
the `/issues` work queue while also appearing on the taxonomy detail page. The
current review round is `contract_v0_reanalysis`; no other taxonomy package is
part of the active review surface.

Current resource-sheet generators:

```bash
PYTHONPATH=. python scripts/generate_readout_font_spritesheet.py
PYTHONPATH=. python scripts/generate_icon_resource_spritesheets.py
PYTHONPATH=. python scripts/generate_illustration_object_spritesheets.py
PYTHONPATH=. python scripts/generate_three_d_object_spritesheets.py
```

These write into:

- `review/task-reviews/assets/fonts/readout_pool_v0/`
- `review/task-reviews/assets/icons/procedural_named/`
- `review/task-reviews/assets/icons/curated_symmetry/`
- `review/task-reviews/assets/icons/curated_non_symmetry/`
- `review/task-reviews/assets/illustrations/object_spritesheets/`
- `review/task-reviews/assets/three_d/object_spritesheets/`
- `review/task-reviews/assets/three_d/named_object_inventory/`

Excel files remain useful for download or archival inspection, but the browser
app does not scrape them. If review sidecars are regenerated, press **Reload
Index**. If app code changed, restart the app.

Solve-rate summaries are best-effort. The app reads the same current locations
used by scene review/status generation when available:

- `review/calibration_sweep_status.json`
- `rlvr/outputs/calibration/current/.../calibration_stats.json`

If those artifacts are absent, task rows show `No solve-rate artifact`.

## Issues and Feedback Storage

Default feedback database:

```text
review/feedback/review_feedback.sqlite
```

The same SQLite database stores task-level audit status. Review audit is
separate from generated artifacts and starts unchecked for every task. A task's
review status passes when the reviewer has checked all non-solve-rate gates:

- prompt
- image
- annotation
- distribution check
- code review
- taxonomy review

The solve-rate review checkbox records that a human has inspected the displayed
solve-rate status and accepted it as operationally sufficient for the task. It
does not replace the generated solve-rate artifact. Domain and scene pages show
two completion counts: review completion from the six non-solve-rate gates,
and solve-rate completion from the separate solve-rate checkbox. Reviewers can
uncheck either status later; the affected completion count immediately becomes
pending again.

The distribution checkbox is initialized from generated artifacts: when
`distribution_review.json` exists and passes, the app treats the distribution
gate as checked by default. If a reviewer saves the audit with Distribution
unchecked, that explicit override wins until the reviewer checks it again. The
task page shows the read-only distribution statistics used for this automatic
gate, including pass/fail status, mode, sample count, checks, query collection
counts, and top answers.
Only gated pass/fail checks are shown in the app. Non-gated numeric diagnostics
such as `max_five_bin_frequency` may remain in `distribution_review.json` for
offline inspection, but they are not decision criteria and should not be shown
as manual-review blockers.

Each comment is keyed to a stable sample identity derived from domain, scene,
task, query, data path, image path, instance seed, prompt, answer, and annotation.
This prevents comments from silently attaching to a regenerated `0000.json`
sample with different content.

Reviewer-facing terminology is **issue**. Browser-facing issue pages use
`/issues`; legacy `/feedback` browser URLs redirect or alias to the issue pages
for compatibility. Implementation-facing names remain `feedback`: API paths are
under `/api/feedback`, and the SQLite tables are `feedback`,
`feedback_comments`, and `feedback_notes`. Do not rename those internals during
normal audit work.

Issue fields:

- category: `prompt`, `annotation`, `rendering`, `answer`, `calibration`, `other`
- severity: `note`, `issue`, `blocker`
- status: `open`, `resolved`
- free-text comment and optional author

The `/issues` page is the minimal issue work queue. It groups actionable
tasks by domain, scene, and task, and shows only these blockers:

- missing manual audit gates for prompt, image, annotation, distribution,
  code review, or taxonomy review;
- solve-rate manual checkbox not checked;
- automated solve-rate artifact missing;
- automated solve-rate artifact present but not accepted;
- open task-level or sample-level issues.

Use the task/sample links to inspect the exact target. Resolve buttons close
only the issue item; they do not mark audit gates or solve-rate review as
passed. Click an issue item or its `thread` link to inspect the reviewer
comment, agent repair notes, add a new agent note, and review the linked
task/sample from one page.
Task pages show open issues, reviewer follow-up comments, and existing repair
notes as compact read-only context. When an open task/sample issue thread
already exists, the nearby reviewer comment box appends to that thread instead
of creating a separate issue item. Use the `Thread` link to open the full
reviewer/agent loop. Add agent repair notes from the issue thread page, not
from the task/sample preview list. The floating task issue panel keeps the
reviewer comment composer outside the scrollable open-issue list so long issue
loops do not hide the input controls.

Resolved issues remain part of the task history. They should no longer appear
as open blockers on `/issues`, but the thread still preserves the original
reviewer comment, reviewer follow-ups, and agent repair notes in chronological
order. Agents may verify resolved status when asked, but should not reopen,
delete, or supersede resolved issues unless the user explicitly requests it.

## Agent Repair Notes

Human issue threads and agent repair notes have different meanings:

- reviewer issue is the request or defect report, and stays `open` until a human
  verifies the updated sample/task and resolves it;
- reviewer follow-up comments continue the same issue thread when the human
  adds more detail or asks another question;
- agent repair notes are append-only implementation notes attached to a feedback
  item after an agent has changed code, prompts, configs, generated artifacts,
  or docs to address that issue.

When an agent acts on a reviewer issue:

1. Make the code/artifact/doc change normally.
2. Regenerate affected task-review artifacts when the rendered sample surface
   changed.
3. Reload the app index after artifact changes, or restart the app after app or
   feedback-schema changes.
4. Add a brief repair note under the relevant issue item. Use one sentence
   that states what changed, which validation/review command ran, whether
   review artifacts were regenerated, and whether the app was reloaded.
5. Do not mark the issue resolved unless the user explicitly asked the agent
   to perform that human-verification step. The normal flow is: agent fixes,
   agent adds repair note, human reviews, human resolves.

If a change addresses a broad task-level issue, add the repair note to the
task-level issue item. If the issue is visible only in one generated
question/image, add the repair note to that sample's issue item.

Export issue records through the feedback API as JSONL:

```bash
curl -H "Authorization: Bearer $TRACE_REVIEW_APP_TOKEN" \
  http://127.0.0.1:7860/api/feedback/export.jsonl
```

Each exported record includes an `agent_notes` array with any repair notes
attached to that issue's underlying feedback id.
