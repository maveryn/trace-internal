---
name: domain-games
description: Use when designing, implementing, or reviewing TRACE games-domain tasks, especially visible dots-and-boxes, bingo, card, domino, Reversi, Connect Four, Checkers, Mancala, Morris, and Go state tasks with local piece-level evidence.
---

# Games Domain

Use this whenever the task lives under `domain=games`.

## Read first
1. `docs/domains/GAMES_TASK_SETUP.md`
2. `docs/project/STATUS.md`
3. `docs/workflows/TASK_AUTHORING.md`
4. `docs/workflows/SHARED_UTILITIES.md`

## Active-contract reminders
- Keep the domain state-first: the visible game pieces should contain the operative information needed to answer the prompt.
- Prefer fully observable, low-convention questions unless a strategic task keeps rules explicit and answer/evidence support broad enough.
- Keep prompt-facing evidence on the visible witness pieces themselves.
- When a wrapped multi-row display has ordered semantics, make the row continuation explicit in both the image and the prompt.
- When a task varies layout scaffold and query type independently, use the chart-style `scene_variant` / `query_variant` split rather than one task id per question stem.
- `docs/domains/GAMES_TASK_SETUP.md` owns the active games contract.

## Practical review checklist
- Check active family/query/evidence details in `docs/domains/GAMES_TASK_SETUP.md` instead of duplicating coverage in the skill.
- Prefer shared game rules helpers in `trace/tasks/games/shared/*_common.py` and renderers in `trace/tasks/games/shared/*_scene.py`.
- Keep game prompts explicit about all non-universal rules such as capture, liberty, sowing, drop, mill, and bracketing rules.
- Add new game-query variants inside an existing task when the visible scaffold and witness semantics stay the same.
- Split only when a new game query changes the perceptual contract enough to be a healthy standalone task.
