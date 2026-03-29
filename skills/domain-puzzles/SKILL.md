---
name: domain-puzzles
description: Use when designing, implementing, or reviewing TRACE puzzle-domain tasks, especially for hidden-rule reasoning families, benchmark-aligned puzzle coverage, and clean evidence contracts for visual puzzle scenes.
---

# Puzzles Domain

Use this whenever the task lives under `domain=puzzles`.

## Read first
1. `docs/project/STATUS.md`
2. `docs/project/TODO.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`
5. `docs/workflows/CODE_REVIEW_GUIDELINES.md`

## Puzzle-domain rules
- Define `task_group` by reasoning family, not by one exact puzzle template.
- Treat puzzles as hidden-rule / hidden-variable reasoning tasks rather than as generic icon grids or mini tables.
- Prefer broad families such as `arithmetic`, `logic`, `spatial`, `topology`, and later `symbolic` over one-off puzzle buckets.
- Reuse the same renderer/layout when multiple puzzle tasks share the same visual grammar; move shared builders into `trace/tasks/puzzles/shared/` as soon as a second task needs them.
- Keep puzzle prompts concise and explicit about the queried unknown, missing slot, or target option.

## Boundary rules
- If the task is mostly direct counting, direct lookup, or direct comparison with no hidden rule, it probably belongs in an existing domain (`icons`, `tables`, `charts`, `tile`, or `geometry`).
- If the task requires inferring a latent arithmetic rule, spatial structure, or option-consistency rule from the figure itself, it is a good fit for `puzzles`.
- Do not duplicate simple icon-style “odd one out” or missing-panel grids unless the puzzle truly depends on row-and-column rule composition rather than object recognition alone.
- Do not force graph-theory or maze tasks into `puzzles` if they are better handled by a graph-specific or tile/path domain.

## Early-family guidance
- `arithmetic`: visual equations, balance/weight puzzles, digit-placement puzzles, number-grid puzzles with explicit unknowns.
- `logic`: option filtering under placement/adjacency/consistency constraints.
- `spatial`: cube views/nets, block stacks, assembly/cut-and-build puzzles.
- `topology`: equivalence under deformation, region/inside-outside reasoning, connected-structure invariants.
- `symbolic` later: letter/word/path puzzles and symbol-mapping tasks once text-rendering needs are clear.

## Evidence rules
- Keep the prompt-facing evidence contract simple and stable within each puzzle family.
- For arithmetic puzzles with an explicit unknown slot, prefer `bbox_set` with exactly one bbox for the queried missing slot.
- For option-based puzzles, evidence should usually ground the queried target option or missing slot rather than a large set of explanatory regions.
- Only use multi-box evidence when the task genuinely needs multiple ordered witnesses and the order can be defined cleanly in the prompt.
- Design early puzzle tasks so the evidence can stay local and visually obvious; avoid families whose first version would need long derived witness sets.

## Design heuristics
- Start with puzzle tasks that expose an explicit queried slot, missing value, or named option. They are easier to verify and keep evidence clean.
- Favor exact-answer construction over perceptual estimation.
- Keep puzzle answer spaces rich enough to avoid collapsing into trivial boolean tasks unless the benchmark value clearly justifies them.
- Push diversity into `task_variant` inside a family before creating new task ids for near-duplicate visual templates.
- If a puzzle family begins to share the same hidden-rule machinery across tasks, promote that rule builder into a family-shared helper instead of copying it task by task.

## Arithmetic-first lessons
- The first arithmetic puzzle tasks should center on explicit unknown slots rather than free-form expression comparison.
- Good early arithmetic variants are those like “what number should replace the question mark?” or “what is the value of the box?” where one queried bbox grounds the answer.
- For a clean first arithmetic contract, prefer one flat equation row with `2..5` boxed operands on the left, one boxed result on the right, and the `?` allowed in either an operand box or the result box.
- For early balance-style arithmetic tasks, prefer `2..3` explicit equality panels with visible `+` and `=` signs plus a final query row rendered like `symbol = ?`; project evidence from the `?` box rather than from the symbol box, and if the row spacing looks too rigid, add only small seeded jitter while keeping the local gaps readable and near-uniform.
- For early arithmetic grid tasks, prefer `3..5` rows with exactly `3` columns and no headers so at least two complete example rows remain after hiding the `?` cell.
- When a puzzle grid repeats a hidden arithmetic row rule, require the complete visible rows to support exactly one operator family; do not accept rows that also fit multiple rule types.
- When an arithmetic unknown-slot family starts feeling too tiny, increase structural variety inside that same one-box contract first: vary operand count, operator mix, and whether the unknown is on the left or right before inventing a new task id.
- Avoid early arithmetic tasks like “largest possible number” or broad expression ranking unless the evidence contract is already well-defined and locally grounded.

## Early logic lessons
- For early logic puzzles, MCQ-style image options are often cleaner than open-vocabulary answers like `"triangle"` or `"red"`.
- If a logic task uses option panels, keep the answer format as `option_letter` and ground prompt-facing evidence on the winning option panel bbox.
- Prefer logic boards with one explicit `?` cell and a stable set of labeled option panels so the user interaction stays consistent even when the hidden rule changes across variants.
- For early logic families, make the semantic rule vary inside `task_variant` (for example row uniqueness vs column uniqueness vs both) before creating new task ids for near-identical board-and-options layouts.

## Early spatial lessons
- For early single-reference cube tasks, do not ask the model to reason about hidden faces the image never reveals.
- If a cube-view task needs full-cube view consistency rather than only visible-corner order, expose the hidden-face structure explicitly in the image first (for example opposite-face hint pairs) before asking about candidate views.
- For option-based spatial puzzles, keep `answer_gt.type = option_letter` and ground prompt-facing evidence on the winning option panel bbox, not on multiple cube faces.
- When a second puzzle family needs labeled image options, reuse shared puzzle option-panel chrome instead of copying panel/label/content-box layout into another scene renderer.

## Benchmark alignment
- MathVision-style useful puzzle coverage includes arithmetic, logic, spatial, topology, and competition-style visual problem solving.
- MathVista-style useful puzzle coverage includes IQ-test / puzzle-figure reasoning, but prefer variants that are structurally distinct from existing icon tasks.
- When in doubt, choose puzzle families that add benchmark-style hidden-rule reasoning without duplicating existing counting/lookup/comparison contracts.

## Coverage reference
For current domain balance and next priorities, use:
- `docs/project/STATUS.md`
- `docs/project/TODO.md`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`
