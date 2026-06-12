# Games Domain Quick Review

Date: 2026-06-09

Scope: quick review of active games-domain taxonomy, prompts, annotation contracts, generated review artifacts, docs, and maintainability risks. This is a backlog note only; no task code was changed as part of this review.

## Summary

- Active games registry is taxonomy-clean: 161 tasks across 50 scenes, with 0 missing taxonomy mappings.
- `review/task-reviews/games` is synchronized with active tasks: 161 task-review directories, 0 missing, 0 stale, 0 wrong-scene directories.
- No stale `evidence` prompt terminology was found in games code/config/docs or generated games review prompts.
- Main remaining issues are unrecorded manual audit status, several annotation-contract review candidates, and code reuse/maintainability hotspots.

## Blocking Active Taxonomy Issues

None found.

Checks run:

- Active default games tasks: 161
- Active games scenes: 50
- `missing_taxonomy_task_ids(list_default_task_ids())`: 0
- Review task dirs under `review/task-reviews/games`: 161
- Missing/stale/wrong-scene review dirs: 0/0/0

## Docs Issues

### 1. Domain Docs Inventory Drift

Resolution: fixed on 2026-06-09 by removing duplicated games task-id inventory from domain docs and pointing readers to `docs/domains/games.md` as the concrete active games scene/task source of truth.

`docs/domains/games.md` matches the active registry exactly: 161 documented games task ids, no extras.

Cross-domain task-boundary policy now lives in core/workflow docs, not in a domain-folder guide.

Recommendation: keep the concrete active inventory only in `games.md` or generated inventory docs.

### 2. Manual Audit State Is Not Recorded

The review feedback DB has:

- Games feedback rows: 0
- Games task-audit rows: 0

This means there are no open games reviewer issues, but also no browser-app manual audit checkboxes recorded for the games tasks. This is process debt, not code/taxonomy drift.

Recommendation: after the next visual pass, record task audit status in the review app so manual audit gates are not only implicit in generated artifacts.

## Prompt Issues

### 1. Prompt Terminology Is Mostly Clean

No generated games prompts sampled under `review/task-reviews/games` contained stale `evidence`, `Evidence format`, or `Required evidence` wording. Prompts use `annotation` / `Required annotation format`.

### 2. Some Prompt Wording Is Still Verbose Or Redundant

Generated Sokoban prompts show repeated scene/rule language, for example:

> The scene shows a Sokoban-style grid with start and goal cells, boxes treated as blockers, and labeled move-sequence options. Use the grid with boxes blocked off. Which option is the shortest S-to-G path?

This is understandable, but it repeats the blocker rule twice. Similar pattern likely exists in other rule-heavy games.

Recommendation: during scene-by-scene prompt polish, keep one concise scene sentence plus one question sentence. Avoid restating the same rule in both scene description and task question unless needed for ambiguity.

### 3. Prompt Build Plumbing Should Stay Scene-Local After Migration

The games scene-package migration moved public task programs into one objective file per task. Prompt construction should therefore live either in the objective file, when it is contract-specific, or in `trace/tasks/games/<scene_id>/shared/` when several objectives in the same scene use the same prompt assembly shape.

This is not a prompt-source violation; active games tasks still use external prompt templates. The remaining risk is repeated prompt/trace glue across sibling objective files after expanding old bundled modules.

Recommendation: when touching a scene, consolidate repeated prompt-building glue into that scene's `shared/` package only if multiple objective files genuinely use the same prompt assembly contract. Do not recreate broad multi-task wrapper modules.

## Annotation Issues

### 1. 2048 Merge Count Annotation Cardinality Does Not Match Answer

Previously, `task_games__2048__merge_count` answered the number of merges, but annotation returned the original tile cells that participated in the merges. Each merge contributed two source-cell boxes, so annotation cardinality was usually `2 * answer`.

Old generated prompt:

> set "annotation" to bounding boxes around the original tile cells that participate in the merges

Old sample:

- Answer: 3
- Annotation boxes: 6

Resolution: changed `task_games__2048__merge_count` and `task_games__2048__score_value` to use `point_pair_set`, with one unordered source-tile center pair per merge. For merge-count queries, annotation cardinality now equals the answer while preserving merge grouping.

### 2. Option-Panel Annotation Should Stay Limited To True Visual Option Tasks

Option-panel annotation remains present for true visual-option tasks such as Sokoban route options, 2048 result boards, Minesweeper reveal outcomes, and Sliding Block result boards. That is consistent with the policy because the answer option is a visible image/panel, not just a prompt-only choice.

Recommendation: during future task additions, keep this boundary strict: do not annotate option labels when the option is only an answer-list encoding; annotate the visual source/target witness instead.

### 3. Mixed Annotation Shapes Are Broad But Expected

Current games review artifacts use:

- `bbox_set`: 8700 samples
- `point_set`: 5800 samples
- `keyed_bbox_map`: 800 samples
- `point_pair_set`: 300 samples
- `keyed_bbox_set_map`: 300 samples
- `point_sequence`: 100 samples
- `keyed_point_set_map`: 100 samples

This diversity is expected for games, but it increases reward/verifier surface area.

Recommendation: add a small generated contract summary per scene/task to docs or review artifacts so future changes can compare annotation type drift automatically.

## Code Quality / Maintainability Issues

### 1. Games Domain Is Large And Several Task Modules Are Monolithic

Games Python line count under `trace/tasks/games`: about 269,253 lines after the scene-package migration. The increase is expected because public objective files now own their task programs instead of routing through old bundled task modules.

Largest modules:

- `trace/tasks/games/cards/trick_winning_play_label.py`: 2996 lines
- `trace/tasks/games/cards/trick_taking_winner_label.py`: 2996 lines
- `trace/tasks/games/cards/same_suit_as_reference_count.py`: 2996 lines
- `trace/tasks/games/cards/poker_draw_card_label.py`: 2996 lines
- `trace/tasks/games/cards/poker_best_hand_label.py`: 2996 lines
- `trace/tasks/games/cards/missing_card_to_complete_hand_label.py`: 2996 lines
- `trace/tasks/games/cards/longest_run_length.py`: 2996 lines
- `trace/tasks/games/cards/higher_than_reference_count.py`: 2996 lines
- `trace/tasks/games/cards/exact_triple_count.py`: 2996 lines
- `trace/tasks/games/cards/blackjack_best_hand_label.py`: 2996 lines

Recommendation: do not refactor these wholesale now, but when touching them:

- Move reusable render/layout helpers into `trace/tasks/games/<scene_id>/shared/` first. Use `trace/tasks/games/shared/` only for helpers reused across multiple scenes.
- Split large rule engines from task-output assembly when a scene has multiple tasks, but keep objective-specific sampling and answer/annotation assembly in the public objective file.
- Keep prompt-building shared where contracts are uniform.

### 2. Shared Style Module Split

Resolution: fixed on 2026-06-09 by keeping `trace/tasks/games/shared/style.py` as a public facade and moving concrete theme families into sibling `style_*.py` modules.

Recommendation: keep importing through the facade unless a scene-local helper has a narrow reason to depend on one style-family module directly.

### 3. Option Layout Was Recently Centralized, But Similar Layout Helpers Should Be Reused More Broadly

`trace/tasks/games/shared/option_layout.py` now handles balanced visual option grids for 2048, Minesweeper, and Sliding Block. Other option-rendering scenes may still use local layout logic.

Recommendation: when touching option-heavy scenes, migrate arbitrary option-card layouts to `option_layout.py` if they are panel/image option sets with flexible option count. Leave board-embedded labels and fixed-column game labels alone.

## Suggested Fix Order

1. Add/record games task manual audit rows after the next review-app pass.
2. Normalize repeated prompt-building helper usage scene-by-scene, without introducing broad wrapper modules.
3. Start opportunistic code-quality cleanup in the remaining largest task modules only when making related functional changes.
