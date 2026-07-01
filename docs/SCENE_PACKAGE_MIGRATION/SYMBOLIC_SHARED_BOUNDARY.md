# Symbolic Shared Boundary

Use this with `SCENE_MIGRATION_GUIDE.md` when migrating a symbolic scene.

## Purpose

The symbolic domain contains compact visual systems with established semantics:
clocks, abaci, Braille cells, automata, music notation, chemistry notation,
probability devices, and logic circuits. These systems share some visual and
notation primitives, but each public scene still has its own renderer grammar
and task contracts.

Scene-package migration must separate four layers:

- true symbolic-domain primitives, such as canvas styling, unit jitter,
  notation drawing adapters, and reusable component geometry;
- reusable visual grammars that belong to one scene, such as a music staff,
  organic structure, dice pair, spinner, logic circuit, Turing tape, or abacus
  board;
- objective-specific task logic, answer binding, annotation binding, prompt
  slots, retries, and final `TaskOutput` construction;
- legacy family routing from folders such as `abacus`, `automaton`, `clock`,
  `notation`, and `probability`.

Public identity remains only:

```text
symbolic -> scene_id -> task_id
task_symbolic__<scene_id>__<objective_contract>
```

Old implementation folders such as `notation` and `probability` are not public
taxonomy nodes. During migration, each active public scene gets its own package
under `trace/tasks/symbolic/<scene_id>/`.

Use `docs/ACTIVE_TASK_INVENTORY.md` for active symbolic scenes and task counts.
Record scene-specific migration findings in review artifacts, not in this
shared-boundary policy.

## Current Active Scenes

Active symbolic scenes currently documented under `docs/tasks/symbolic/` are:

| Scene | Active tasks | Current source family |
|---|---:|---|
| `abacus` | 3 | `trace/tasks/symbolic/abacus/_lifecycle.py` plus `trace/tasks/symbolic/abacus/{displayed_value_readout,place_digit_readout,target_value_match_label}.py` |
| `agent_automaton` | 2 | `trace/tasks/symbolic/agent_automaton/{agent_final_pose_label,future_grid_label}.py` |
| `braille_cell` | 3 | `trace/tasks/symbolic/braille_cell/{braille_word_read_label,matching_pattern_label,word_braille_match_label}.py` |
| `clock` | 9 | `trace/tasks/symbolic/clock/{offset_readout,full_time_readout,alarm_wait_time_value,hand_angle_value,time_extremum_label,equivalent_time_label,elapsed_time_value,sequence_completion_label,time_order_label}.py` |
| `dice` | 7 | `trace/tasks/symbolic/dice/{dice_conditional_event_value,pair_attribute_combo_probability,pair_difference_probability,pair_sum_probability,pair_sum_threshold_probability,single_attribute_probability,single_threshold_probability}.py` |
| `life_automaton` | 2 | `trace/tasks/symbolic/life_automaton/{life_future_grid_label,one_step_cell_state_count}.py` |
| `logic_gate_circuit` | 4 | `trace/tasks/symbolic/logic_gate_circuit/{gate_type_count,internal_output_count,output_value_label,satisfying_assignment_label}.py` |
| `morse_code` | 2 | `trace/tasks/symbolic/morse_code/{morse_word_read_label,word_morse_match_label}.py` |
| `music_staff` | 12 | `trace/tasks/symbolic/music_staff/{note_name_label,interval_name_label,transposed_pitch_pair_count,key_signature_label,scale_validation_count,scale_degree_function_label,chord_quality_label,chord_inversion_label,roman_numeral_label,duration_equivalence_label,meter_type_count,articulation_symbol_label}.py` |
| `organic_structure` | 2 | `trace/tasks/symbolic/organic_structure/{bond_order_count,ring_size_count}.py` |
| `radial_code_wheel` | 3 | `trace/tasks/symbolic/radial_code_wheel/{code_output_label,missing_code_symbol_label,output_code_match_label}.py` |
| `spinner` | 4 | `trace/tasks/symbolic/spinner/{single_attribute_probability,multi_attribute_and_probability,multi_attribute_or_probability,spinner_pair_event_value}.py` |
| `truth_table` | 3 | `trace/tasks/symbolic/truth_table/_lifecycle.py` plus `trace/tasks/symbolic/truth_table/{equivalent_expression_label,satisfying_row_count,truth_pattern_label}.py` |
| `turing_tape` | 2 | `trace/tasks/symbolic/turing_tape/{final_head_position_value,turing_written_symbol_count}.py` |

These source families are implementation history only. Do not migrate to
`trace/tasks/symbolic/notation/` or `trace/tasks/symbolic/probability/` as
scene packages.

## Domain Shared

`trace/tasks/symbolic/shared/` is for symbolic-domain helpers reused by
multiple unrelated scenes. Domain shared code must be scene-neutral and
identity-free. It must not know or branch on public task ids, public query ids,
objective contracts, registered task classes, sibling scene identities,
task-specific answer schemas, or task-specific prompt wording. It must not
construct final public `TaskOutput`.

Approved domain-shared categories:

- generic symbolic canvas/background/style adapters;
- coordinate-preserving unit-size jitter and low-level drawing wrappers;
- reusable primitive geometry for notation-like marks when reused by multiple
  scenes;
- neutral option-panel and panel-label helpers, when reused by multiple
  symbolic scenes;
- scene-neutral word-option sampling helpers for notation readout tasks, when
  the helper only constrains token candidates and does not know the notation
  renderer or objective contract;
- small annotation serialization adapters reused by multiple symbolic scenes,
  when a repo-global helper is not already sufficient;
- pure math helpers for fractions, finite-state tables, probability labels, or
  angle arithmetic, only when they are not tied to one scene grammar.

Text/token vocabularies that are not specific to a symbolic scene should use
repo-global task helpers under `trace/tasks/shared/`. For example, Braille and
Morse word-option tasks derive short lowercase alphabetic tokens from
`trace.tasks.shared.word_assets`, which itself filters the shared
`assets/labels` manifests and caps each length bucket to common leading labels.
Braille and Morse currently use 1000 candidates for each length `3`, `4`, and
`5`. Do not maintain separate scene-local word banks for these notation readout
tasks.

Domain-shared modules that may remain domain-shared after narrowing:

| Module | Target role |
|---|---|
| `scene_style.py` | Symbolic canvas, panel, and background style adapters. |
| `visual_defaults.py` | Cross-scene symbolic rendering defaults only. |
| `unit_size_jitter.py` | Coordinate-preserving unit-size jitter helpers. |
| `drawing.py` | Thin re-export or wrapper layer only, if still needed after scenes migrate. |
| `common.py` | Generic config/template loading and neutral sampling helpers only; remove task-id/query-id routing as scenes migrate. |
| `word_option_sampling.py` | Scene-neutral same-prefix word-option sampling for Morse/Braille readout and matching tasks. |

Domain-shared modules that should move to scene-local shared when their owning
scene is migrated:

| Module | Scene-local target |
|---|---|
| `abacus_scene.py` | Retired by the `abacus` scene package; keep bead/column geometry scene-local unless another symbolic scene proves reuse. |
| `braille_scene.py` | Retired by the `braille_cell` scene package; keep Braille specs, rendering, and annotation helpers scene-local. |
| `clock_scene.py` | Retired by the `clock` scene package; keep clock-face specs, rendering, layout, and annotation helpers scene-local. |
| `dice_scene.py` | Retired by the `dice` scene package; dice rules live in `dice/shared/rules.py`, and dice rendering lives in `dice/shared/rendering.py`. |
| `logic_gate_scene.py` | Migrated into `logic_gate_circuit/shared/{state,rules,rendering,annotations,output,prompts,styles}.py`. |
| `music_notation_scene.py` | Migrated into `music_staff/shared/{state,rules,sampling,styles,components,annotations,prompts}.py`; keep staff geometry and notation rendering scene-local unless another symbolic scene proves reuse. |
| `organic_structure_scene.py` | Migrated into `organic_structure/shared/{state,rules,rendering,annotations,prompts,output,sampling,styles}.py`; keep organic line-angle grammar scene-local unless another symbolic scene proves reuse. |
| `spinner_scene.py` | Migrated into `spinner/shared/{rendering,annotations,prompts,defaults,rules}.py`. |

Legacy family modules retired by scene-package migration:

| Module | Target |
|---|---|
| `trace/tasks/symbolic/automaton/shared.py` | Retired. Agent, Life, and Turing tape helpers live in direct scene packages. |
| `trace/tasks/symbolic/automaton/cellular_automaton.py` | Retired. Do not add compatibility imports for migrated scenes. |
| `trace/tasks/symbolic/automaton/turing.py` | Retired by `trace/tasks/symbolic/turing_tape/{final_head_position_value,turing_written_symbol_count}.py` and `trace/tasks/symbolic/turing_tape/shared/`. |

## Scene Shared

`trace/tasks/symbolic/<scene_id>/shared/` owns one scene's visual grammar and
scene-specific reusable primitives.

Recommended symbolic scene-shared role files match the current symbolic file
policy:

- `state.py`
- `sampling.py`
- `rules.py`
- `layout.py`
- `rendering.py`
- `annotations.py`
- `prompts.py`
- `output.py`
- `defaults.py`
- `styles.py`
- `assets.py`
- `components.py`
- `relations.py`
- `metrics.py`
- `transforms.py`
- `spatial_primitives.py`
- `option_rendering.py`

`_lifecycle.py` is the only allowed private scene-root helper. Use it only when
several public tasks in the same scene share one visual lifecycle and each
public task file still owns the objective contract.

Scene shared may know the scene grammar, such as a music staff, abacus board,
Braille cell, logic circuit, spinner, dice pair, automaton grid, Turing tape,
clock face, or organic structure. It must not route behavior by public task id,
public query id, objective contract, public task name, or registered class.

Scene shared must not:

- accept or branch on public `task_id`;
- accept or branch on public `query_id`;
- export public query-id routing tables;
- register public tasks;
- construct final public `TaskOutput`;
- contain task-named runtime files;
- hide copied public task bodies.

If a helper needs to know which public query branch is running, the public task
file should resolve the branch to neutral semantic arguments and pass those
arguments into shared code.

Example:

- Bad shared argument: `query_id="pair_sum_at_least_probability"`.
- Good shared arguments: `operator="greater_than"`, `target_sum=8`,
  `dice_values=(...)`, `candidate_outcomes=(...)`.

## Public Task Files

Each public task file owns one objective contract:

- literal public `TASK_ID`;
- `SCENE_ID`;
- local `SUPPORTED_QUERY_IDS`;
- query selection and query validation;
- objective-specific target/candidate construction;
- answer binding;
- `annotation_gt` binding;
- dynamic prompt slots and prompt/query key selection;
- task-specific trace fields;
- retry and final `TaskOutput`.

Public task files may call scene-shared and domain-shared primitives. They must
not delegate objective behavior to a shared base task whose subclasses differ
only by class attributes, forced query ids, task ids, or answer-schema
constants.

## Legacy Shared Surfaces To Audit

During symbolic scene migration, audit these source patterns first:

- large multi-task modules such as `music_staff.py`, `dice.py`, `spinner.py`,
  `logic_gate.py`, and `organic_structure.py`;
- shared base tasks such as `_SymbolicBaseTask`, `_DiceProbabilityBaseTask`,
  `_SpinnerProbabilityBaseTask`, and `_LogicGateBaseTask`;
- helper functions that branch on public `task_id`, public `query_id`, or
  task-specific answer schema;
- task-output rewrite helpers used to map legacy source variants to public
  query ids;
- family-level config loaders that use task ids to select generation defaults;
- prompt helper code that selects user-facing prose from task ids or query ids
  inside shared modules.

Public task wrappers around a shared base task are not enough. During migration,
the public task file must own the objective logic directly, or pass
objective-owned hooks into a permitted `_lifecycle.py` without making lifecycle
code route on sibling public identity.

## Config And Prompt Migration

Migrated symbolic scene packages use one scene-local config per scene, such as:

```text
configs/domains/symbolic/abacus.yaml
configs/domains/symbolic/dice.yaml
configs/domains/symbolic/organic_structure.yaml
configs/domains/symbolic/spinner.yaml
configs/domains/symbolic/turing_tape.yaml
```

Scene-package migration should create or update one config per public scene:

```text
configs/domains/symbolic/<scene_id>.yaml
```

Do this only for the assigned scene. Do not reshape every symbolic config as
part of one scene migration. Configs should hold scene/task generation and
rendering knobs, but no public task routing, query routing, objective dispatch,
or task coverage. Remove config-level `query_id_weights` and
`balanced_query_id_sampling` for migrated review-candidate scenes unless a
later global policy explicitly allows them.

Prompt assets should likewise move toward scene-scoped bundles such as:

```text
prompts/symbolic/<scene_id>/symbolic_<scene_id>_v1.json
```

Prompt prose stays in prompt assets. Public task files provide dynamic slots
and selected prompt/query keys.

## Suggested Migration Order

Start with small scenes that validate symbolic boundaries before touching the
large notation and probability modules:

1. `abacus`
   - two public tasks;
   - tests single-board readout and option-panel selection using one shared abacus scene grammar.
2. `braille_cell`
   - two public tasks;
   - small option/count scene with clear annotation contracts.
4. `logic_gate_circuit`
   - two public tasks;
   - good test for moving rule evaluation into scene shared while keeping
     objective-specific answer/annotation binding in task files.
5. `clock`
   - one public scene for single-clock readout, multi-clock extremum, ordering,
     and analog/digital match-panel tasks;
   - keep clock geometry reusable without preserving legacy rewrite plumbing.
6. Automaton-style scenes are migrated as direct scene packages:
   `life_automaton`, `turing_tape`, and `agent_automaton`.
   - do not recreate `automaton/shared.py` or compatibility import surfaces.
7. `spinner`
   - probability rendering and exact rational answer formatting need careful
     scene-local contracts.
8. `organic_structure`
   - chemistry notation renderer and graph-like molecule constraints need a
     scene-local rules layer.
9. `music_staff`
   - migrated to a scene package with one public task file per objective;
   - use it as the reference for keeping large notation renderers scene-local
     while public task files own objective/query, answer, and annotation
     binding.

## Scene Migration Procedure For Symbolic

For each symbolic scene:

1. Inventory active task ids, current source files, config keys, prompt bundle,
   tests, docs, and review artifacts.
2. Write the scene contract: visual grammar, semantic system, layout/view,
   style axes, and annotation projection assumptions.
3. Write one task contract per public task: answer schema, annotation schema,
   query ids, reasoning program, and objective-owned logic.
4. Move scene grammar into scene `shared/` role files.
5. Keep or import only approved identity-free domain shared primitives.
6. Rewrite each public task file so it owns objective logic and final public
   output fields.
7. Remove retired wrappers, compatibility aliases, stale prompt/config keys,
   and stale review artifacts for that scene.
8. Smoke-generate every public task and supported query branch.
9. Add the scene to the review-candidate registry only after the source shape
   is ready for the migration gate.
10. Record manual code audit, taxonomy review, and migration-test status under
    `review/task-reviews/symbolic/<scene_id>/`.
11. Generate review artifacts only after manual and automated gates pass.
12. Reload the review app index.

Do not mark a symbolic scene accepted from source code. Human review in the
browser app is still required.
