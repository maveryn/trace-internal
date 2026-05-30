---
name: domain-games
description: Use when designing, implementing, or reviewing TRACE games-domain tasks, especially board, card, arcade, and visible game-state tasks with local piece-level evidence.
---

# Games Domain

Use this whenever the task lives under `domain=games`.

## Read first
1. `docs/domains/GAMES_TASK_SETUP.md`
2. `docs/ACTIVE_TASK_INVENTORY.md` for the generated active scene/task list.
3. `docs/project/STATUS.md`
4. `docs/workflows/TASK_AUTHORING.md`
5. `docs/workflows/SHARED_UTILITIES.md`
6. `docs/workflows/PUZZLE_GAME_RENDERING_UPGRADE.md` when touching repeated-cell or board-style renderers

## Active-contract reminders
- Keep the domain state-first: the visible game pieces should contain the operative information needed to answer the prompt.
- Prefer fully observable, low-convention questions unless a strategic task keeps rules explicit and answer/evidence support broad enough.
- Keep prompt-facing evidence on the visible witness pieces themselves.
- When a wrapped multi-row display has ordered semantics, make the row continuation explicit in both the image and the prompt.
- Treat the public taxonomy as `domain=games -> scene_id -> task_id`; task-review artifacts live under `review/task-reviews/games/<scene_id>/<task_id>/`.
- Split tasks under the same scene when the reasoning algorithm or answer/evidence contract changes. Keep only mirror knobs such as player color, row/column axis, board size, threshold direction, or style as params/query diagnostics inside one task.
- `docs/domains/GAMES_TASK_SETUP.md` owns the active games contract.

## Practical review checklist
- Check active family/query/evidence details in `docs/domains/GAMES_TASK_SETUP.md` instead of duplicating coverage in the skill.
- Prefer shared game rules helpers in `trace/tasks/games/shared/*_common.py` and renderers in `trace/tasks/games/shared/*_scene.py`.
- Use `docs/ACTIVE_TASK_INVENTORY.md` for the current active scene ids when checking review artifacts.
- Keep game prompts explicit about all non-universal rules such as capture, liberty, sowing, drop, mill, and bracketing rules.
- Add new query params inside an existing task only when the visible scaffold, reasoning algorithm, and witness semantics stay the same.
- Use `trace/tasks/games/shared/fixed_query_task.py` when a shared renderer exposes several narrow public tasks.
- For repeated board/cell/unit renderers, follow `docs/workflows/PUZZLE_GAME_RENDERING_UPGRADE.md` so style and size jitter remain non-semantic and evidence-safe.
