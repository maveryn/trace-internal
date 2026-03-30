---
name: domain-games
description: Use when designing, implementing, or reviewing TRACE games-domain tasks, especially visible card and domino state tasks with local piece-level evidence.
---

# Games Domain

Use this whenever the task lives under `domain=games`.

## Read first
1. `docs/domains/GAMES_TASK_SETUP.md`
2. `docs/domains/TASK_FAMILY_VARIANTS.md`
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`

## V1 games-domain policy
- Keep the domain state-first: the visible game pieces should contain the operative information needed to answer the prompt.
- Prefer low-convention counting/comparison questions over strategy-heavy or hidden-information rules in the first games tasks.
- Keep prompt-facing evidence on the visible witness pieces themselves.
- When a wrapped multi-row display has ordered semantics, make the row continuation explicit in both the image and the prompt.
- When a task varies layout scaffold and query type independently, use the chart-style `scene_variant` / `query_variant` split rather than one task id per question stem.

## Current coverage
- `bingo`
  - `task_games_bingo_completed_line_count`
- `cards`
  - `task_games_cards_hand_count`
- `dominoes`
  - `task_games_dominoes_chain_count`

## Shared helpers to prefer
- `trace/tasks/shared/support_sampling.py`
- `trace/tasks/shared/variant_sampling.py`
- `trace/tasks/shared/text_rendering.py`
- `trace/tasks/games/shared/bingo_common.py`
- `trace/tasks/games/shared/bingo_scene.py`
- `trace/tasks/games/shared/card_scene.py`
- `trace/tasks/games/shared/domino_scene.py`
- `trace/tasks/games/shared/style.py`
- `trace/tasks/games/shared/visual_defaults.py`
- `trace/tasks/games/shared/complexity.py`

## Pair with
- `skills/task-design/SKILL.md`
- `skills/task-complexity/SKILL.md`
- `skills/task-implementation/SKILL.md`
- `skills/verification-review/SKILL.md`
