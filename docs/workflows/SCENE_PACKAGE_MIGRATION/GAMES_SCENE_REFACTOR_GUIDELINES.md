# Games Scene Refactor Guidelines

This is the games-domain companion to
`SCENE_REFACTOR_GUIDELINES.md`. It applies while migrating scenes under:

```text
trace/tasks/games/<scene_id>/
configs/domains/games/<scene_id>.yaml
review/task-reviews/games/<scene_id>/
```

Use it as the target structure for `2048` first, then copy the same role
boundaries scene-by-scene where they fit.

## Games Scene Package Shape

Most games scenes should use this structure:

```text
trace/tasks/games/<scene_id>/
  <objective_contract>.py
  ...
  shared/
    defaults.py
    state.py
    mechanics.py
    sampling.py
    rendering.py
    prompts.py
    annotations.py
    output.py
```

Only create files that are useful for the scene. A small scene can omit
`annotations.py` or `output.py` if the public task files are clearer without
them.

## Games Identity Boundary

Games scene `shared/` modules must be identity-free. They may receive semantic
game arguments, but they must not receive public task/query identity.

Forbidden in `trace/tasks/games/<scene_id>/shared/`:

- function arguments named `task_id`, `query_id`, `supported_query_ids`, or
  `objective_contract`;
- constants such as `SUPPORTED_*_QUERY_IDS` that act as public-query routers;
- branches like `if query_id == ...`, `if task_id == ...`, or
  `if objective_contract == ...`;
- helpers that choose answer, annotation, prompt, target, or candidate logic
  from public task/query names.

Allowed games-style arguments:

- `player`, `piece_color`, `target_status`, `move_direction`, `dice_roll`,
  `ship_shape`, `card_rank`, `card_suit`, `candidate_cells`, `option_count`,
  `hidden_fleet`, `board_size`, and other scene-semantic values;
- typed scene state or mechanics results, such as move outcomes, scoring
  outcomes, fleet placements, path results, merge events, or legal destination
  sets.

The public task file owns query-id resolution and translates query branches
into semantic arguments before calling shared helpers. Shared helpers process
the semantic arguments without knowing which public task/query produced them.

## Games Prompt Boundary

Games scenes follow the shared scene-package prompt-asset gate in
`README.md`.

Games task files may select prompt template keys and provide dynamic slots
derived from generated state, such as player color, marked piece label, target
ship name, dice roll, move direction, option labels, score values, row/column
labels, or target object names.

Scene `shared/prompts.py`, when present, should be a thin identity-free adapter
around prompt assets and common prompt rendering. It should not know public
task/query identity and should not own game-specific wording.

## File Responsibilities

### `defaults.py`

Scene-local code fallbacks only for shared game-board grammar and rendering.
YAML remains source of truth.

Games examples:

- board/cell/token size fallback values;
- small scene-level numeric or structural fallback constants.

Do not keep task-owned fallbacks here. Games examples that belong in public
task files or `task_overrides.<task_id>` include:

- answer support fallback tuples;
- option-count fallback tuples used by one task;
- target-answer balancing supports;
- feasibility bounds used only for one objective.

Supported query ids belong in public task files or task-local modules, following
the shared scene-package no-query-weight gate.

For example, a Battleship board-size support is scene grammar, but sunk-ship
answer support, named-cell hit/unhit branches, and last-cell option count are
task-owned.

Do not keep broad `_TaskDefaults` dataclasses in public task files or in
catch-all shared modules.

### `state.py`

Scene state, typed contracts, stable ids, and validation.

Games examples:

- board size constants;
- piece, token, card, cell, path, projectile, or stack dataclasses;
- result dataclasses such as move outcomes or scoring outcomes;
- entity-id helpers such as cell ids, piece ids, option ids;
- sample validation that does not choose task answers.

### `mechanics.py`

Pure game rules and transformations.

Games examples:

- move simulation;
- legal destination enumeration;
- capture, merge, hit, clear, score, collision, or path mechanics;
- board-key normalization;
- connectivity and reachability primitives.

Mechanics must not build prompts, annotations, or `TaskOutput`.

### `sampling.py`

Axis resolution and neutral construction helpers.

Games examples:

- resolve scene/style/player/direction axes;
- construct a board with requested primitive properties;
- build candidate boards or option sets without deciding the public objective;
- sample distractor states.

Sampling may expose helpers like `board_for_merge_values(...)` or
`build_result_board_options(...)`. It must not expose `generate_score_output`
or a `sample_for_query(query_id)` dispatcher that owns multiple public task
contracts. It also must not accept `query_id`, `supported_query_ids`, or public
task names as routing inputs.

### `rendering.py`

Game renderer, render params, themes, and render maps.

Games examples:

- board or table renderer;
- option-board renderer;
- token/piece/card style variants;
- calls into existing games shared layout, style, text, marker, and option
  layout helpers.

Rendering must update entity geometry consistently with layout jitter and
style changes. Annotation must always be projected from render maps, never from
hardcoded pre-jitter coordinates.

### `prompts.py`

Prompt loading and prompt artifact assembly, only as a thin identity-free
adapter around external prompt assets.

Games examples:

- prompt bundle lookup;
- merge external static slots with public-task dynamic slots;
- prompt rendering through shared prompt infrastructure;
- prompt trace metadata.

Prompt text and prompt schema ownership follow the shared scene-package prompt-asset gate.
New text must use `annotation`, not `evidence`.

### `annotations.py`

Scene-local annotation projection helpers.

Games examples:

- map board cells to center points or boxes;
- map candidate option labels to option bboxes;
- project move paths, merge pairs, or selected pieces from render maps;
- build keyed annotations only when roles matter.

This file may project witnesses, but public task files still decide which
witnesses are the correct witnesses for the objective.

### `output.py`

Common games scene output assembly, only if objective-neutral.

Allowed:

- assemble common trace sections;
- include rendered scene entities, render map, prompt metadata, answer,
  annotation, background/noise metadata, and task versions;
- accept already-bound answer and annotation artifacts from the public task.

Forbidden:

- branching by public task id, objective contract, or top-level query id;
- accepting public task id, objective contract, or top-level query id as
  routing inputs;
- choosing target objects;
- computing the task answer;
- replacing public task files with shared full-output functions.

## Public Game Task Files

Each `trace/tasks/games/<scene_id>/<objective_contract>.py` must:

- define exactly one registered public task class;
- set `domain = "games"` and `scene_id = "<scene_id>"`;
- own the objective-specific sampling loop and semantic constraints;
- bind final `answer_gt`;
- bind final `annotation_gt`;
- call shared renderer/prompt/output helpers only after the objective is
  already determined;
- provide only dynamic prompt slots and selected prompt template keys to the
  prompt renderer;
- expose meaningful `query_id` only for narrow operand variants inside the
  same objective contract.
- translate any query-id branch into semantic arguments before calling scene
  shared helpers.

Do not use fixed-query wrappers or query-subset mixins in migrated games
scenes.

Identity-free scene helpers may remain in scene `shared/` even with one current
caller when they are reusable scene primitives. Do not split or move helpers
purely because of caller count or file length.

## 2048 Target Structure

Use `2048` as the first fully cleaned exemplar:

```text
trace/tasks/games/2048/
  max_tile_value.py
  merge_count.py
  move_result_board_label.py
  score_value.py
  shared/
    defaults.py
    state.py
    mechanics.py
    sampling.py
    rendering.py
    prompts.py
    annotations.py
    output.py
```

Expected placement for `2048`:

- `state.py`: `SIZE`, `EMPTY`, board/coord aliases, move result/sample
  dataclasses, cell ids, validation.
- `mechanics.py`: slide/merge simulation, max tile, board keys, result-source
  tracing.
- `sampling.py`: axis resolution, score decomposition, merge-board
  construction, result-board distractor construction.
- `rendering.py`: 2048 render params, tile themes, board and option-board
  rendering.
- `prompts.py`: 2048 prompt examples and prompt artifact builder.
- `annotations.py`: source merge point pairs, max-tile source boxes, selected
  result-board option boxes.
- `output.py`: common 2048 `TaskOutput` assembly only.

Public task ownership:

- `merge_count.py`: target merge count, board construction call, merge-count
  validation, integer answer, point-pair annotation.
- `score_value.py`: target score, score decomposition call, score validation,
  integer answer, point-pair annotation.
- `max_tile_value.py`: target max tile, unique-max validation, integer answer,
  source-cell bbox annotation.
- `move_result_board_label.py`: option count/label choice, result-board option
  construction, selected label answer, selected option bbox annotation.

## Domain Shared Promotion Candidates

During the scene loop, record possible promotions but do not move new code into
`trace/tasks/games/shared/` immediately.

Likely games-domain candidates:

- visual MCQ option-panel layout for 4/6 option boards;
- unit-size scaling and slack-based layout jitter plumbing;
- panel background/style resolution;
- marker/highlight drawing primitives;
- text legibility and font selection wrappers;
- generic named-axis and support sampling wrappers;
- common card/piece/board rendering primitives, only after two cleaned scenes
  independently need the same API.

Keep scene-local:

- any named game rules;
- scene state dataclasses;
- board topology specific to one game;
- scoring rules specific to one game;
- prompt examples specific to one scene;
- annotation projection tied to one scene's entity ids.

At the final games-domain checkpoint, compare all recorded candidates and
promote only narrow primitives reused by at least two cleaned games scenes.

## Games Scene Completion Note

Each completed games scene section in `games.md` should include:

```text
Completion note:
- source ownership:
- split/merge decision:
- scene shared helpers:
- domain shared candidates deferred:
- config/prompt/docs updated:
- query weights removed:
- prompt wording/static slots externalized:
- complexity removed:
- task reviews regenerated/stale folders purged:
- checks:
- blockers:
```

The `domain shared candidates deferred` line is required even when it says
`none`. This keeps promotion decisions explicit and prevents accidental
one-scene abstractions from moving into domain shared too early.
