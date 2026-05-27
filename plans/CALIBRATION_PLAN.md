# TRACE Domain Calibration Plan

This is the only current calibration plan for TRACE. Non-current calibration
notes and smoke-status files must not be used as acceptance criteria.

## Purpose

Calibrate TRACE domain by domain, scene by scene. For each domain we first
audit and fix prompt composition, then make the existing tasks pass the
distribution gates, then consider new tasks from Vero-600k coverage, then rerun
a within-domain uniqueness and complexity audit. A domain is marked done only
after all active tasks in that domain pass calibration and the domain
complexity scores have been updated.

Calibration is manual. Do not run automatic tuning loops. Make config changes
only after inspecting task-review samples, model failures, and per-query
breakdowns, and only after the reviewer specifies the change. A narrow scripted
adjustment is acceptable only when the reviewer asks for it and one or two
obvious knobs clearly explain the failure.

The human reviewer owns task tuning and task-selection decisions. Agents may
summarize failures, propose config changes, and propose Vero-derived task
candidates, but they must not tune configs, add new tasks, or remove tasks until
the reviewer gives an explicit instruction for that scene.

## Current Models

Use `qwen25vl7b` as the only current calibration model for all future domain,
scene, and task calibration. Existing `qwen3vl4b` comparison results are not
required for future acceptance and should not be regenerated just to satisfy
current calibration.

| model key | model | response cap | server ports | max model len |
| --- | --- | ---: | ---: | ---: |
| `qwen25vl7b` | `Qwen/Qwen2.5-VL-7B-Instruct` | `2048` | `8002` | `4096` |

Prompt length budget is `2048` tokens for every task under the current model.

Current acceptance decisions use the Qwen2.5 model row above. Qwen3 probe
outputs are outside the current acceptance gate.

### Single-GPU vLLM Endpoint

This machine has one calibration GPU. Run one qwen25 server on GPU 0 and port
`8002`; all calibration agents should share it through the runner's endpoint
lock instead of starting more servers.

Server command:

```bash
mkdir -p logs/vllm logs/vllm/locks
setsid bash -lc 'exec env CUDA_VISIBLE_DEVICES=0 \
  TRANSFORMERS_NO_TF=1 \
  TOKENIZERS_PARALLELISM=false \
  VLLM_WORKER_MULTIPROC_METHOD=spawn \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
    --host 127.0.0.1 \
    --port 8002 \
    --served-model-name Qwen/Qwen2.5-VL-7B-Instruct \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --dtype auto' \
  > logs/vllm/qwen25vl7b_8002.log 2>&1 < /dev/null &
echo $! > logs/vllm/qwen25vl7b_8002.pid
```

Readiness check:

```bash
python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://127.0.0.1:8002/v1/models", timeout=5).read().decode()[:1000])
PY
```

Run calibration with `--probe-backend openai_server --models qwen25vl7b`.
The default endpoint pool is the single endpoint
`http://127.0.0.1:8002/v1`, so concurrent agents will contend on
`logs/vllm/locks/qwen25vl7b_8002.lock` and wait when the endpoint is busy.

## Acceptance Gates

Each task is accepted only if `qwen25vl7b` passes all gates on the same `100`
sampled task instances with `24` rollouts per instance.

Prompt budget preflight:

- `0 / 100` sampled prompts exceed `2048` tokens for `qwen25vl7b`.

The four acceptance conditions are:

1. Response cap rate is `<= 0.25`.
2. Hard-question fraction is `< 0.30`, where hard means `0 / 24` successful
   rollouts for that question.
3. Easy-question fraction is `< 0.20`, where easy means `> 18 / 24`
   successful rollouts for that question.
4. Mean solve rate is `0.15 <= mean <= 0.75` over all `2400` rollouts.

A task that fails prompt length or response cap is `blocked` until prompt,
rendering, density, or output-format issues are fixed. A task that passes those
but misses hard/easy/mean gates is `needs_manual_tuning`.

## Calibration Baseline And Artifact Freshness

The current repo state starts a fresh calibration and TRACE-owned version
baseline named `v0`. Prompt bundles, TRACE schema/version fields, taxonomy
version wording, instance versions, reward contracts, and calibration artifacts
must all use `v0` unless a future repo-wide migration explicitly changes the
baseline.

All current task-review, distribution, solve-rate, and scene-review artifacts
must be generated from the current code/config and tagged with
`calibration_baseline: "v0"` in their manifests or stats files. Artifacts that
do not carry this exact baseline metadata are stale and must not be reused for
acceptance, even if their filenames look current.

Freshness policy:

1. Before running a scene or task for the `v0` baseline, delete or regenerate
   stale active artifacts for that scope:
   - `plans/task-reviews/<domain>/<scene_id>/<task_id>/`
   - `plans/task-reviews/<domain>/<scene_id>/scene_review.xlsx`
   - `out/calibration/current/<domain>/<scene_id>/<task_id>/`
   - `rlvr/outputs/calibration/current/<model>/<domain>/<scene_id>/<task_id>/`
   - scoped entries in `plans/calibration-status/` or the aggregate sweep
     status that do not declare the current baseline.
2. Failed probe outputs are discarded before retry. Do not archive failed
   configs next to the active artifacts during the current calibration pass.
3. Do not copy solve rates from older task ids, renamed tasks, removed tasks,
   pre-refactor configs, or artifacts without the current baseline metadata.
4. After a `v0` artifact exists for a task, any task/config/rendering/prompt
   change that can plausibly affect samples or difficulty invalidates that
   task's `v0` artifact. Delete the stale active task artifacts before
   regenerating fresh `v0` artifacts from the current code/config.
5. If a rerun is purely documentation cleanup and cannot affect generation,
   prompts, rendering, verifier payloads, or model outputs, keep the existing
   calibration label and record that no solve-rate claim changed.

The sweep runner defaults to `--calibration-baseline v0`. It treats existing
probe, review, and stats files without matching baseline metadata as stale.

### Controlled Unanswerable Branches

Some lookup-style tasks may include controlled unanswerable samples when the
normal answer type can remain unchanged, such as returning the string
`unanswerable` for a missing label. These branches must be explicit in task
metadata, prompts, verifier traces, and evidence payloads. The trace should
record why the target is absent, and projected evidence should stay consistent
with the task contract rather than pointing at unrelated visual regions.

Calibration probes use an internal per-sample cursor so the task-review
workbook and solve-rate run share the same deterministic answerable versus
unanswerable mix. Do not pass sampler-control params by hand; use the
calibration runner so the build path injects the cursor safely.

## Domain Definition Of Done

A domain is done only when all of these are true:

1. Domain prompt templates and prompt composition have been audited for awkward,
   redundant, stale, or duplicated wording.
2. Every scene has passed the human review gate: the reviewer inspected the
   generated task-review workbook prompts/images and approved solve-rate
   probing for that scene.
3. Every scene has had an explicit visual-randomization review covering safe
   opportunities for non-semantic variation such as color palettes, sizes,
   spacing, background style, line style, and coordinate-preserving noise.
   Proposed visual variation changes must be reviewer-approved before they are
   implemented.
4. Every active default task in the domain passes the prompt preflight and all
   four acceptance gates for `qwen25vl7b`.
5. Every scene has a current scene review workbook at
   `plans/task-reviews/<domain>/<scene_id>/scene_review.xlsx`.
6. Each scene review workbook has a first sheet named `model_stats`, followed
   by one sheet per task in that scene. The task sheets include `100` sampled
   rows per task so the scene review matches the standard calibration sample
   size.
7. Vero-600k has been reviewed for the domain, with decisions recorded for
   existing-scene task additions and new-scene candidates.
8. New tasks or scenes selected from the Vero review have been explicitly
   approved by the reviewer, implemented, reviewed, calibrated, and accepted.
9. The domain has been audited for duplicate or over-split tasks under the
   public taxonomy `domain -> scene_id -> task_id`.
10. Complexity scoring has been updated for every task in the domain.
11. Each task has at most six complexity axes.
12. Any complexity axis with weight `< 0.05` has been removed.
13. Complexity score has at least `0.40` correlation with model difficulty for
    every task in the domain, where model difficulty is `1 - solve_rate`.

Use Spearman correlation by default for the complexity pass because the scores
are meant to rank relative difficulty, not fit a linear scale.

## Pre-Solve Deep Audit Gate

Run this gate before answer-distribution checks and solve-rate calibration for
each scene. Do not use solve-rate results to accept a task until the visual,
prompt, contract, sampling, and artifact checks below are clean.

### A. Prompt And Contract

1. Prompt text must use the current scene/task/query composition and must not
   contain stale task-family wording or obsolete `task_variant` fields. The public task unit is
   `task_id`; task-internal branches are `query_id` or query variants.
2. The final prompt must not repeat the same scene description, target
   instruction, or answer-format rule in multiple layers.
3. Prompt, rendered image, answer schema, evidence schema, and verifier trace
   must agree exactly.
4. Every task must keep one stable public answer schema and one stable public
   evidence schema across all query branches. If a branch needs a different
   answer or evidence format, it is not the same task.
5. Decimal answers must explicitly require exactly one digit after the decimal
   point when that is the task contract. Do not ask for approximate constants
   such as `pi = 3.14`, and do not display approximation shortcuts in the
   image unless the task explicitly tests reading that displayed value.
6. Multiple-choice options must be rendered in the image, not listed only in
   the prompt, and every MCQ task must provide at least five visible options.
7. If the image contains a visible `?` marker or blank target, treat it as a
   target locator by default, not prompt-facing evidence. Evidence should point
   to the visual information used to derive the answer, such as given values,
   labeled points, marked lines, curves, axes, ticks, surrounding patches, or
   other source witnesses. Include the `?` marker only when localizing the
   unknown slot is itself part of the grounding contract, such as a missing
   patch or blank position. If the marker is useful for debugging but not for
   scoring, record it in trace metadata with a field such as
   `target_locator_bbox` rather than exposing it as prompt-facing evidence.
   For analytical geometry and other construction-heavy tasks, evidence should
   prefer the minimal visible givens needed for the computation; if no local
   witness makes sense, treat that as a task/evidence-contract issue to clean
   up during the domain pass.
8. Controlled unanswerable branches must keep the same answer/evidence schema
   as the task, state the unanswerable behavior in the prompt, and record the
   absence reason in trace metadata.

### B. Visual Rendering

1. Text-bearing tasks must sample fonts from the shared font assets. Use one
   font family per meaningful text block such as chart labels, table cells,
   option labels, legends, section headers, or callout text. Do not use ad hoc
   fonts unless the task documents an exclusion for readability.
2. Option labels, candidate labels, legend text, object labels, and other
   answer-bearing text must also use shared font assets.
3. Board, panel, chart, graph, and page styles must have non-semantic visual
   variety where safe: backgrounds, palette families, frames, line weights,
   grid strokes, shadows, gutters, and mild noise.
4. Rendered content should not be fixed at the same centered position on every
   sample. Use safe layout or placement jitter after ensuring evidence is
   projected from the final layout.
5. Labels, ticks, values, option text, and evidence overlays must not overlap
   answer-bearing marks or become unreadable at max configured density.
6. Semantic colors must remain separable under all sampled palettes. Do not let
   background/style variation collapse meaningful color distinctions.
7. Domain-specific background designs should be reviewed scene by scene. Add or
   update background families when a domain still looks visually uniform, but
   do not make readability worse.
8. For charts, graphs, and pages, inspect the amount and placement of
   distractor/context text. Use headers, captions, sidebars, callouts, source
   notes, and decorative snippets only when they cannot be confused with the
   task target.
9. Scenes with named objects should use as broad a suitable object/name pool as
   the scene grammar supports, including icons, 3D objects, page entities,
   labels, and object categories. Avoid repeatedly sampling a tiny name/object
   subset unless the task requires it.
10. Generate shared inspection sheets for reusable visual resources such as
    font families, icon/object pools, 3D object resources, palettes, and
    background/style packs. Store these under `plans/task-reviews/shared/` or a
    clearly documented equivalent inspection folder.

### C. Sampling And Distribution

1. Candidate answer support and input support should be continuous across the
   intended range. Avoid discontinuities such as `4..8` plus `10` unless the
   task semantics require a structured support like even numbers, card ranks,
   dice sums, or legal board sizes.
2. Run answer-distribution checks before solve-rate calibration. Check the
   overall answer distribution and the distribution broken down by `query_id`,
   scene variant, style variant, chart/map/board type, object count, option
   count, and other task-specific difficulty knobs.
3. Query branches should not collapse to very different answer supports unless
   that is explicitly intended and documented.
4. Unique final answers must be guaranteed by construction. Do not rely on
   retries that merely hide ambiguous samples without explaining the constraint.
5. Zero-answer and unanswerable cases must be intentional, documented, and
   supported by evidence semantics rather than introduced as sampler accidents.
6. Review max-density samples separately from random samples for crowding,
   overlap, prompt length, and evidence projection.

### D. Evidence And Trace

1. Answer and evidence must come from the same execution trace.
2. Prompt-facing evidence must be visually meaningful, local, and inside the
   final rendered canvas.
3. Evidence bboxes/points/sequences must be computed after final layout,
   scaling, placement jitter, style chrome, and image composition.
4. Evidence should identify the visual witnesses used to derive the answer, not
   unrelated context or a whole panel unless the whole panel is the natural
   witness.
5. Verifier payloads must use metadata and projections as source of truth, not
   rendered pixels.
6. Trace metadata must record all explicit random choices that affect prompt,
   scene, rendering, query branch, answer construction, and evidence.

### E. Assets, Shortcuts, And Maintainability

1. Asset pools must have documented provenance and compatible licenses before
   becoming part of generation.
2. Public prompts and rendered images must not leak the answer through file
   names, hidden labels, debug text, metadata rendered into the image, or
   deterministic naming conventions.
3. Task modules must not hardcode user-facing prompt text; use external prompt
   bundles.
4. Shared rendering, style, font, label, and object helpers should live at the
   narrowest reusable layer that fits. Do not duplicate helper logic across
   sibling tasks.
5. Tests should cover the real active contract, including prompt/image
   agreement, option count for MCQs, decimal formatting, evidence projection,
   and deterministic generation for fixed seeds.

## Domain Prompt Audit

Run this before any scene calibration or Vero-driven expansion in a domain.

1. Review all scene, task, and query prompt templates used by the domain.
2. Generate a small prompt-only sample across scenes and tasks, then read the
   final composed prompts exactly as the model sees them.
3. Fix awkward or redundant wording, especially repeated scene descriptions,
   duplicated answer-format instructions, stale task-family language, and
   prompts that restate the same requirement in both the scene and task layer.
4. Preserve the prompt architecture: one reusable scene layer, one task layer,
   and an optional query layer. The scene layer should say what is displayed;
   the task/query layer should ask for the target reasoning result.
5. Keep user-facing text in external prompt assets, not hardcoded in task
   modules.
6. Keep answer-format instructions centralized and avoid per-task duplication
   unless the task has a genuinely special answer contract.
7. After prompt edits, regenerate task-review workbooks before using any
   previous solve-rate result for current acceptance.

Prompt cleanup should improve clarity without making the task easier by adding
extra semantic hints or worked examples.

## Chart Rendering Variation Checklist

Use this addendum when the current domain is `charts`. It complements the
shared information-scene workflow in
`docs/workflows/INFORMATION_SCENE_RENDERING_UPGRADE.md` and the open chart
coverage notes in `plans/coverage-extension/charts.md`.

For each chart scene, inspect and report whether these layers can safely vary
before making any rendering change:

1. Canvas and page background:
   - avoid using only white or near-white/off-white backgrounds;
   - include visibly distinct but readable light palette families such as cool,
     warm, mint, lavender, blue-gray, publication gray, parchment/editorial, and
     high-contrast light;
   - use dark themes only with explicit scene-level approval and contrast
     inspection.
2. Plot, chart, and panel backgrounds:
   - avoid every plot area staying pure white;
   - allow plot/panel/card fills to vary independently from the outer canvas;
   - preserve readability of axes, grid lines, guide lines, value labels,
     legends, printed cells, highlights, and evidence overlays.
3. Semantic mark colors:
   - protect colors that encode series, categories, regions, heatmap values,
     legends, or answer-bearing groups;
   - vary non-semantic chrome freely, but vary semantic palettes only through
     task-owned palette logic with separation checks.
4. Chart chrome:
   - consider axis, grid, tick, border, guide-line, title, legend, frame,
     shadow, and callout color variation;
   - keep these choices independent of answer value, correct option, query id,
     and difficulty bucket.
5. Typography:
   - use the shared font assets from `assets/fonts/`;
   - sample one font family per meaningful text block, such as chart labels,
     axes/ticks, legend, option set, panel title, or context box;
   - avoid dense or decorative fonts where labels are small or crowded.
6. Context and distractors:
   - consider report/news/dashboard/app-window framing, captions, source notes,
     sidebars, callout boxes, decorative metric snippets, and irrelevant
     numbers only when they do not alter the task contract;
   - use `assets/context_text/`, record bboxes/source/font metadata, and keep
     distractors outside semantic chart marks unless explicitly scoped in.
7. Layout and spacing:
   - use bounded layout jitter, reserved-margin context, or computed content
     frames only when evidence bboxes are recomputed after final layout;
   - avoid coordinate-changing transforms unless that scene has explicit bbox
     transform tests.
8. Texture and noise:
   - use only coordinate-preserving paper/scan/grid/noise effects;
   - ensure texture does not hide small labels, thin bands, map boundaries,
     heatmap cells, error bars, or uncertainty intervals.
9. Known chart rendering fixes:
   - recheck scene-specific issues from `plans/coverage-extension/charts.md`,
     including crowded legends, tiny labels, weak highlights, thin flow bands,
     label overlap, and overly uniform chart backgrounds.

After any approved chart rendering change, regenerate the scene review workbook
before solve-rate probing.

## Scene Calibration Loop

Work on one domain at a time and one scene at a time.

1. Confirm the domain prompt audit has been completed after the latest prompt
   template or composition change.
2. Enumerate the current active tasks for the scene from the registry and
   taxonomy.
3. Generate or refresh the task-review workbooks for all tasks in the scene
   using current code/config. Each public task workbook must use the same
   `100` random task instances used for calibration, not `100` samples per
   `query_id`. If a task has multiple `query_id` values, the workbook may keep
   one sheet per `query_id`, but the combined row count across all sheets for
   that public task must be `100`.
   The calibration runner must first validate answer distribution on the exact
   exported `100`-row RLVR parquet with
   `scripts/check_rlvr_probe_distribution.py`. This is a hard prerequisite
   before solve-rate probing. If the first 100 rows fail only because of sample
   skew, the runner may generate additional same-sampler validation shards of
   `100` rows with new seeds and validate the cumulative distribution at
   `200`, `300`, `400`, and `500` rows. These extra rows are distribution
   validation only; they are not used for task-review workbooks or solve-rate
   probing.
4. Build the combined scene review workbook with one sheet per task. Include
   `100` deterministic random rows per task. When the task has a current
   calibration workbook, those rows should come from the same `100` calibration
   instances. The scene workbook should therefore contain
   `100 * number_of_tasks_in_scene` inspection rows, plus the `model_stats`
   sheet when model results exist.
   After any reviewer-approved new task or new scene is implemented, generate
   this scene review workbook before ending the implementation pass, even if
   solve-rate calibration will happen later.
5. Review the scene for safe non-semantic visual randomization opportunities:
   color/palette variety, object sizes, spacing, background or panel styling,
   line/marker styles, typography, context/distractor text, and
   coordinate-preserving noise. For chart scenes, use the chart rendering
   variation checklist above and explicitly call out canvas palette, plot/panel
   background, semantic color protection, typography, context, layout, texture,
   and any chart-specific rendering fixes. Report whether more visual variety is
   possible and useful for this scene. Do not implement visual-randomization
   changes unless the reviewer explicitly approves them.
6. Stop and report the workbook path plus the visual-randomization assessment.
   The reviewer inspects the prompts/images in the workbook before any
   solve-rate run.
7. If the reviewer requests prompt, image, or rendering fixes, implement only
   those requested fixes, regenerate the scene workbook, and repeat the review
   gate.
8. Run solve-rate probing only after the reviewer explicitly says the scene
   workbook looks ready.
9. Run or refresh `100 x 24` model rollouts for `qwen25vl7b`. Reuse the exact
   same `100` task instances shown in the task-review workbook.
   The answer-distribution gate must already pass and be linked from the sweep
   status before any model endpoint is claimed. If cumulative validation still
   fails after `500` rows, stop and report the task as distribution-failed or
   blocked; do not change task config, alter sampling, or run solve-rate probing
   during that calibration run.
   If the scene contains multiple tasks and multiple matching vLLM endpoints
   are free, the task probes may run in parallel across those endpoints/GPUs.
   Do not serialize every task through one endpoint by habit; rely on the
   endpoint-pool locks to claim available servers safely. If all endpoints for a
   model are busy, the runner should wait for a free endpoint rather than
   bypassing the pool. If no calibration GPU or endpoint is available during a
   scene review handoff, record the scene as `solve_rate_pending_gpu` and defer
   the solve-rate run, but do not mark the scene accepted and do not advance to
   the next scene as if calibration passed. The next step for that scene remains
   running or refreshing solve-rate calibration.
10. Add the model stats as the first sheet in the scene review workbook.
11. For failing tasks, inspect and report:
   - task images and prompts,
   - prompt-token and response-token stats,
   - hard/easy/mean/cap failures by model,
   - per-`query_id` breakdowns,
   - important scene/config knobs,
   - examples near the failure boundary.
12. Do not tune failing tasks immediately. Wait for the reviewer to specify the
   exact config or task-design change to try.
13. After the reviewer specifies a change, implement it, regenerate review
   artifacts as needed, and rerun calibration only for changed tasks.
14. Repeat until every existing task in the scene is accepted, deferred, or
   explicitly removed by the reviewer.
15. Move to the next scene only after the current scene reaches one of those
   explicit end states.

Do not copy solve rates from removed task ids, stale query variants, or
non-current configuration versions onto current tasks.

## Post-Scene Domain Audit

Run this after every scene in a domain has reached an explicit accepted,
deferred, or removed state, and before marking the domain done. This audit is a
domain-level pass over prompts, visual noise, task overlap, and artifact
freshness. It is intentionally separate from per-scene calibration because
problems often appear only when the whole domain is viewed side by side.

Required inputs:

- current default-enabled task ids from the registry,
- current domain/task-group configs,
- prompt bundles for every task group in the domain,
- latest scene review workbooks,
- latest `100 x 24` qwen2.5 solve-rate artifacts,
- latest generated trace shards or task-review JSON rows for every scene.

Audit steps:

1. Confirm the public inventory:
   - count active task ids for the domain from the registry,
   - count accepted rows in `plans/PROGRESS_SUMMARY.md`,
   - verify every accepted row has the current public taxonomy
     `domain -> scene_id -> task_id`,
   - verify no removed task remains default-enabled.
2. Re-audit prompt composition over the full domain:
   - run a prompt-concision sample across all domain tasks,
   - run the prompt/evidence contract audit when available,
   - read the longest rendered prompts exactly as the model sees them,
   - remove repeated scene/task language, stale query wording, and redundant
     output instructions,
   - require every answer+evidence prompt to contain a named
     `Evidence format:` section with a concrete pixel-space example.
3. Re-audit evidence format and projection:
   - evidence must be in final-image pixel space,
   - allowed public evidence shapes are `bbox_set`, `point_set`,
     `point_sequence`, or `point_pair_set` unless a task has an explicitly
     documented exception,
   - labels, ids, graph coordinates, and semantic witnesses may remain in
     trace metadata, but not as prompt-facing evidence,
   - sampled evidence overlays must align with visible image objects.
4. Re-audit domain visual noise:
   - identify the domain-level post-render noise policy in
     `configs/domains/<domain>/base.yaml`,
   - the expected default is `apply_prob: 0.5` for every domain, scene, task
     group, and task,
   - verify every scene/task group loads that domain policy unless a task has
     an explicit documented exception,
   - any task-specific noise override must keep evidence coordinates valid and
     must document the reason for deviating from `apply_prob: 0.5`,
   - sample current generated instances and inspect
     `render_spec.post_image_noise.apply_prob`,
   - inspect current accepted trace artifacts too, because existing scene
     artifacts can silently retain stale noise settings,
   - only coordinate-preserving post-render edits are allowed: blur,
     downsample, jpeg, and additive/noise-like edits. Do not use crop,
     translation, rotation, perspective, padding, or any edit that invalidates
     point/bbox evidence.
5. Re-audit task redundancy:
   - compare every pair of tasks in the domain by scene grammar, given
     quantities, target quantity, reasoning operation, answer type, evidence
     shape, and uniqueness constraints,
   - keep separate task ids only when the visual scene, reasoning target, or
     evidence contract is materially different,
   - if two tasks differ only by surface wording, direction, threshold side, or
     another branch of the same objective, merge them under one task with
     separate `query_id` values,
   - remove over-split tasks before the domain is marked done.
6. Record a domain audit note under
   `plans/task-reviews/<domain>/domain_post_scene_audit.md` with:
   - date,
   - active task count,
   - scene list,
   - prompt audit commands and results,
   - noise policy and trace-level noise findings,
   - redundancy decisions,
   - unresolved caveats and required refreshes.
7. Update `plans/PROGRESS_SUMMARY.md` with the audit-note path and any caveats
   that affect interpretation of current solve-rate artifacts.

If prompt text, rendering, task design, or generation config changes during the
post-scene audit, regenerate the affected task/scene review workbooks. Rerun
solve-rate probes for any change that can plausibly affect model difficulty or
answer extraction; otherwise record the change as a prompt/documentation-only
cleanup with no new solve-rate claim.

## Vero-600k Review Loop

Use the current domain notes under `plans/coverage-extension/` before adding
tasks inspired by Vero-600k. If fresh Vero question metadata is needed, rerun
the Vero review scripts and keep generated review outputs out of source-of-truth
planning unless they are refreshed against the current taxonomy.

For each domain:

1. Review Vero examples and template clusters relevant to the current scene.
2. First propose new tasks for existing TRACE scenes.
3. Only after existing-scene opportunities are exhausted, propose new scenes
   and their tasks.
4. Exclude ideas that require natural images, free-form answers, unverifiable
   evidence, or benchmark-specific artifacts TRACE cannot synthesize cleanly.
5. Shortlist only tasks with enough Vero coverage and a clear metadata-grounded
   verifier contract.
6. Confirm each candidate is sufficiently different from existing tasks in the
   same domain.
7. Stop and ask for reviewer confirmation before implementing any new Vero
   candidate.
8. Implement only reviewer-approved new tasks or scenes, then immediately
   generate the lightweight scene review workbook for the affected scene. Do
   not leave a newly implemented task/scene without a current scene review
   artifact.
9. Continue with the same scene review and calibration loop after reviewer
   inspection.

A new task can be justified by different reasoning, a different answer/evidence
contract, or a clearly different visual scene. If the task only changes surface
wording or mirror query direction, keep it inside an existing task as
`query_id`.

Vero analysis is advisory until the reviewer approves a candidate. Do not add a
new task solely because it appears in Vero coverage.

## Task Uniqueness Audit

After all scenes in a domain pass calibration, audit the domain again.

For every pair of tasks in the domain, check:

- scene grammar and visual appearance,
- given quantities,
- target quantity,
- transformation/reasoning operation,
- answer type and uniqueness constraints,
- evidence payload shape,
- whether the difference belongs in `query_id` instead of `task_id`.

Merge or remove over-split tasks before the domain is marked done. Do not leave
removed tasks in default generation.

## Complexity Pass

Run the complexity pass only after the domain task set is stable.

1. Define compact domain/scene-level axes first.
2. Add task-local axes only when the shared axes do not capture the actual
   observed difficulty.
3. Keep at most six axes for any task.
4. Remove axes with weight `< 0.05`; such low-weight axes are bookkeeping noise.
5. Compute correlation between complexity score and `1 - solve_rate` using the
   latest accepted calibration artifacts.
6. Target Spearman correlation `>= 0.40` for every task in the domain.
7. If a task misses the target, adjust complexity formulas only. Do not
   regenerate solve rates unless task generation or config changes.

Record the complexity result and any dropped axes in the domain progress notes.

## Persistent vLLM Server Pool

On this calibration machine, keep the Qwen2.5 vLLM server resident
permanently. Do not let calibration agents load models directly. The one vLLM
server owns the one local GPU, and agents only send OpenAI-compatible client
requests to the already-running server.

Server layout:

Current verified calibration host: `1 x NVIDIA A100-SXM4-80GB`, one
`Qwen/Qwen2.5-VL-7B-Instruct` vLLM process on GPU `0`. Launch it as a detached
`setsid` job so it survives the command session.

| pool key | model | GPU | port | max model len | response cap |
| --- | --- | ---: | ---: | ---: | ---: |
| `qwen25vl7b` | `Qwen/Qwen2.5-VL-7B-Instruct` | `0` | `8002` | `4096` | `2048` |

Write server logs and PIDs under `logs/vllm/`. The model should be loaded once
and left running. Calibration agents must not stop or restart the server unless
explicitly asked.

Launch commands:

```bash
mkdir -p logs/vllm logs/vllm/locks

setsid bash -lc 'exec env CUDA_VISIBLE_DEVICES=0 \
  TRANSFORMERS_NO_TF=1 \
  TOKENIZERS_PARALLELISM=false \
  VLLM_WORKER_MULTIPROC_METHOD=spawn \
  vllm serve Qwen/Qwen2.5-VL-7B-Instruct \
    --host 127.0.0.1 --port 8002 \
    --served-model-name Qwen/Qwen2.5-VL-7B-Instruct \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --dtype auto' \
  > logs/vllm/qwen25vl7b_8002.log 2>&1 < /dev/null &
echo $! > logs/vllm/qwen25vl7b_8002.pid
```

Before launching calibration jobs, verify the current Qwen2.5 server is live:

```bash
python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://127.0.0.1:8002/v1/models", timeout=5).read().decode()[:1000])
PY
```

### Endpoint Claiming

Agents coordinate with file locks under `logs/vllm/locks/`. The lock is the
source of truth for whether an endpoint is occupied. The lock file contents are
only human-readable metadata.

When `scripts/run_task_calibration_sweep.py` uses `--probe-backend
openai_server` and no explicit `--server-base-url`, it now automatically:

1. selects the pool for the requested model,
2. claims the first unlocked endpoint in that pool,
3. writes lock metadata with `pid`, `task_id`, `model_slug`, and endpoint,
4. runs the probe against that endpoint,
5. releases the lock when the probe process exits, even on failure.

If all endpoints for a model are in use, the runner waits and retries every
`--server-pool-wait-interval` seconds. Do not pass `--server-base-url` for
normal calibration runs, because doing so bypasses pool selection. Use an
explicit server URL only for debugging one endpoint.

Useful lock knobs:

```bash
--server-pool-lock-root logs/vllm/locks
--server-pool-wait-interval 30
--no-server-pool-locks  # debugging only; do not use for shared calibration
```

To inspect claimed endpoints:

```bash
for lock in logs/vllm/locks/*.lock; do
  [ -s "$lock" ] && { echo "== $lock =="; cat "$lock"; }
done
```

If an agent process is killed, the OS releases its `flock` automatically. A
new runner may overwrite stale lock metadata when it acquires that endpoint.

To stop the persistent server only when explicitly requested:

```bash
kill $(cat logs/vllm/qwen25vl7b_8002.pid)
```

## Sweep Commands

Normal shared-machine runs should use the endpoint pool. Do not pass
`--server-base-url`; the runner claims one free endpoint for the current model and
releases it when the model pass completes.

This machine has one compatible endpoint, so scene-level task probes are
serialized through port `8002`. Keep using the endpoint pool and locks; when
another agent holds `logs/vllm/locks/qwen25vl7b_8002.lock`, wait for the runner
to acquire it instead of hard-pinning or bypassing the lock.

Run the current calibration model for a scoped scene:

```bash
PYTHONPATH=. python scripts/run_task_calibration_sweep.py \
  --scene <domain>/<scene_id> \
  --probe-backend openai_server \
  --models qwen25vl7b
```

Equivalent explicit Qwen2.5 run:

```bash
PYTHONPATH=. python scripts/run_task_calibration_sweep.py \
  --probe-backend openai_server \
  --models qwen25vl7b \
  --max-tokens 2048 \
  --max-model-len 4096
```

Useful scoped options:

```bash
# Dry-run inventory.
PYTHONPATH=. python scripts/run_task_calibration_sweep.py --dry-run

# Run one task.
PYTHONPATH=. python scripts/run_task_calibration_sweep.py \
  --probe-backend openai_server \
  --models qwen25vl7b \
  --max-tokens 2048 \
  --max-model-len 4096 \
  --tasks <task_id>

# Resume from a task.
PYTHONPATH=. python scripts/run_task_calibration_sweep.py \
  --probe-backend openai_server \
  --models qwen25vl7b \
  --max-tokens 2048 \
  --max-model-len 4096 \
  --start-at <task_id>
```

Qwen3 scoped runs are comparison runs only and must be requested
explicitly. They are not part of current task acceptance.

The runner writes aggregate status to:

- `plans/calibration_sweep_status.json`
- `plans/calibration_sweep_status.md`

Scoped per-task, experimental, or rerun-specific status summaries should be
written under `plans/calibration-status/` using explicit `--status-json` and
`--status-md` paths. Do not add new `calibration_sweep_status_*` files at the
`plans/` root.

For each task, `scripts/run_task_calibration_sweep.py` validates answer
distribution before solve-rate probing and writes:

- `<task>_calib100_seed<seed>.parquet.distribution_report.json`

The first check is always the realized `100` calibration rows. If that fails,
the runner may build up to four additional same-sampler validation shards of
`100` rows each and recheck the cumulative distribution up to `500` rows. The
hard gates are `unique_answers >= 5` and `max_answer_frequency < 1/3`, applied
to the cumulative validation rows and to each observed/expected `query_variant`
slice when trace metadata provides variants. Solve-rate calibration still uses
only the original `100` calibration rows. A task that still fails after `500`
rows must be reported as distribution-failed or blocked; agents must not tune,
relax constraints, or change answer sampling inside the calibration run.

The scene workbook is the human-review surface. The status files are summaries,
not a replacement for inspecting samples and model outputs.

## Artifact Rules

Current calibration artifacts use baseline label `v0` unless the reviewer
explicitly starts a new task-local calibration label after a code/config change.
Every generated review manifest and solve-rate stats file must record
`calibration_baseline`.

Current task-review artifacts belong under:

`plans/task-reviews/<domain>/<scene_id>/<task_id>/`

Current scene-review workbooks belong at:

`plans/task-reviews/<domain>/<scene_id>/scene_review.xlsx`

Scoped calibration status summaries belong under:

`plans/calibration-status/`

All active status files must identify the same `calibration_baseline` as the
artifacts they summarize. Status rows without that baseline are historical and
must be regenerated or removed before they are used in a scene workbook.

When a task is split, merged, renamed, or removed:

- delete stale active-review folders for removed ids,
- do not leave removed ids in default generation,
- do not transfer non-current solve rates to new task ids,
- regenerate review workbooks from current code/config,
- update task docs, taxonomy, configs, and progress notes in the same domain
  pass.

## Notes

1. Complexity correlation is defined here against `1 - solve_rate` from
   `qwen25vl7b`, the only current calibration model.
2. The Vero review currently stores sampled metadata and question templates, not
   all image bytes. Download images only when domain review genuinely needs
   visual inspection beyond the saved metadata.
