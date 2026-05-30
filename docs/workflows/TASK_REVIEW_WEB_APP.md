# Task Review Web App

The task-review web app is the browser replacement for workbook-first manual
inspection. It reads the active review sidecars under `review/task-reviews` and
persists reviewer feedback in a separate SQLite database.

## Default Review Workflow

For new tasks, renderer changes, prompt changes, or distribution-changing
logic, generate the normal task-review sidecars, then review them in the app:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

Then use this review loop:

1. Generate review artifacts under `review/task-reviews` as usual.
2. If anything under `review/task-reviews` changed, click **Reload Index** in
   the app or call `POST /api/reload`.
3. Inspect through the browser app by domain, scene, task, and query id.
4. Use task and sample pages to review image, prompt, answer, evidence,
   distribution status, solve-rate status, and manual-audit status.
5. Save sample-specific feedback in the app so comments are keyed to the exact
   sample identity; do not use Excel notes as the default feedback channel.
6. Mark manual-audit checkboxes only after prompt, image, evidence,
   distribution, and solve-rate review are acceptable.
7. Treat a task as complete only when all manual audit gates pass and the
   current solve-rate artifact is accepted.
8. Use Excel workbooks only as optional static exports for archival, sharing
   outside the app, or fallback debugging.
9. If web-app code, templates, CSS, JavaScript, indexer logic, resource
   indexing, feedback storage, or schemas changed, restart the app instead of
   only reloading the index.
10. After reload or restart, verify the affected domain/scene/task/sample page
    shows the updated local files, statuses, and feedback controls before
    handing off.

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

Remote access:

```bash
export TRACE_REVIEW_APP_TOKEN='<shared-review-token>'
export TRACE_REVIEW_APP_BASE_URL='/proxy/7860'  # when using Jupyter Server Proxy
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

- If anything under `review/task-reviews` changes, click **Reload Index** or call
  `POST /api/reload` before inspecting or handing off the app URL. This includes
  task samples, images, `data/*.json`, manifests, distribution files, solve-rate
  artifacts, scene review manifests, and files under `review/task-reviews/assets`.
- The app shows a `Review artifacts changed` banner when files under
  `review/task-reviews` are newer than the loaded index. Treat that banner as a
  blocker for visual inspection until **Reload Index** has run.
- If review-app code changes, restart the server. This includes templates,
  CSS/JS, server routes, indexer logic, resource indexing, feedback storage, and
  schema changes.
- After either refresh path, open the affected domain/scene/task/sample page and
  verify the displayed image/prompt/evidence/status reflects the local files.
- Feedback comments, manual audit checkboxes, theme changes, and ordinary
  navigation do not require **Reload Index**.

## Data Sources

The app scans:

- `review/task-reviews/<domain>/<scene_id>/scene_review_manifest.json`
- `review/task-reviews/<domain>/<scene_id>/<task_id>/manifest.json`
- `distribution_review.json` and `random_review_100.json` when present
- `data/<query_id>/*.json`
- `images/<query_id>/*.png`

Domain discovery is registry-driven: only public active domains listed in
`trace.core.taxonomy.ACTIVE_DOMAINS` are eligible for task-review indexing.
Folders under `review/task-reviews` that are not active domains, including
`review/task-reviews/assets`, are reserved for separate resource review surfaces
and do not affect domain, scene, task, sample, or default search counts.

The separate **Resources** link opens `/resources`, which scans
`review/task-reviews/assets` for review-only images and JSON manifests such as
font contact sheets, icon sheets, illustration object sheets, and other support
assets. Resource files are served only through stable indexed ids under
`/resources/media/<asset_id>`; they are not task samples and do not use sample
feedback.

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

Excel files remain useful for download or archival inspection, but the browser
app does not scrape them. If review sidecars are regenerated, press **Reload
Index**. If app code changed, restart the app.

Solve-rate summaries are best-effort. The app reads the same current locations
used by scene review/status generation when available:

- `review/calibration_sweep_status.json`
- `rlvr/outputs/calibration/current/.../calibration_stats.json`

If those artifacts are absent, task rows show `No solve-rate artifact`.

## Feedback

Default feedback database:

```text
review/feedback/review_feedback.sqlite
```

The same SQLite database stores task-level manual audit status. Manual audit is
separate from generated artifacts and starts unchecked for every task. A task's
manual audit passes only when the reviewer has checked all task-level gates:

- prompt
- image
- evidence
- distribution check
- solve-rate review

The solve-rate review checkbox records that a human has inspected the displayed
solve-rate status and accepted it as operationally sufficient for the task. It
does not replace the generated solve-rate artifact. A task is shown as completed
only when all manual audit gates pass and the current solve-rate artifact is
accepted. Reviewers can uncheck any manual audit gate later; the task
immediately becomes pending again even if solve-rate remains accepted.

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
task, query, data path, image path, instance seed, prompt, answer, and evidence.
This prevents comments from silently attaching to a regenerated `0000.json`
sample with different content.

Feedback fields:

- category: `prompt`, `evidence`, `rendering`, `answer`, `calibration`, `other`
- severity: `note`, `issue`, `blocker`
- status: `open`, `resolved`
- free-text comment and optional author

The `/feedback` page is the minimal work queue. It groups actionable tasks by
domain, scene, and task, and shows only these blockers:

- missing manual audit gates for prompt, image, evidence, or distribution;
- solve-rate manual checkbox not checked;
- automated solve-rate artifact missing;
- automated solve-rate artifact present but not accepted;
- open task-level or sample-level feedback.

Use the task/sample links to inspect the exact target. Resolve buttons close
only the feedback item; they do not mark audit gates or solve-rate review as
passed. Click a feedback item or its `thread` link to inspect the reviewer
comment, agent repair notes, add a new agent note, and review the linked
task/sample from one page.
Task pages show open feedback, reviewer follow-up comments, and existing repair
notes as compact read-only context. When an open task/sample feedback thread
already exists, the nearby reviewer comment box appends to that thread instead
of creating a separate feedback item. Use the `Thread` link to open the full
reviewer/agent loop. Add agent repair notes from the feedback thread page, not
from the task/sample preview list. The floating task-feedback panel keeps the
reviewer comment composer outside the scrollable open-feedback list so long
feedback loops do not hide the input controls.

## Agent Repair Notes

Human feedback and agent repair notes have different meanings:

- reviewer feedback is the issue or request, and stays `open` until a human
  verifies the updated sample/task and resolves it;
- reviewer follow-up comments continue the same feedback thread when the human
  adds more detail or asks another question;
- agent repair notes are append-only implementation notes attached to a feedback
  item after an agent has changed code, prompts, configs, generated artifacts,
  or docs to address that feedback.

When an agent acts on reviewer feedback:

1. Make the code/artifact/doc change normally.
2. Regenerate affected task-review artifacts when the rendered sample surface
   changed.
3. Reload the app index after artifact changes, or restart the app after app or
   feedback-schema changes.
4. Add a brief repair note under the relevant feedback item. Use one sentence
   that states what changed and whether review artifacts were regenerated or the
   app was reloaded.
5. Do not mark the feedback resolved unless the user explicitly asked the agent
   to perform that human-verification step. The normal flow is: agent fixes,
   agent adds repair note, human reviews, human resolves.

If a change addresses a broad task-level issue, add the repair note to the
task-level feedback item. If the issue is visible only in one generated
question/image, add the repair note to that sample's feedback item.

Export feedback as JSONL:

```bash
curl -H "Authorization: Bearer $TRACE_REVIEW_APP_TOKEN" \
  http://127.0.0.1:7860/api/feedback/export.jsonl
```

Each exported feedback record includes an `agent_notes` array with any repair
notes attached to that feedback id.
