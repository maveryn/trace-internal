# Contributing to Trace

## Purpose
This file is the short developer workflow and pre-commit checklist for day-to-day contributions.

## Development workflow
1. Start from repo root and install dependencies:

```bash
pip install -r requirements.txt
```

2. Implement focused changes in the correct locations:
- task code: `trace/tasks/<domain>/<scene_id>/<objective_contract>.py`
- prompt bundles: `prompts/<domain>/...`
- domain config: `configs/domains/<domain>/...`
- task docs: `docs/tasks/<domain>/<scene_id>/<task_id>.md`

3. Reuse shared helpers before adding task-local utilities:
- `trace/core/`
- `trace/tasks/shared/`
- `trace/tasks/<domain>/shared/`
- scene-local `shared/` packages
- `docs/contracts/SYSTEM_ARCHITECTURE.md`

4. Follow current source-layout and review boundaries while implementing:
- `docs/workflows/CODE_REVIEW_GUIDELINES.md`
- `docs/contracts/SOURCE_LAYOUT.md`

5. Keep prompts externalized (no hardcoded prompt strings in task modules).

6. Update docs when behavior/contracts change:
- `docs/README.md`
- relevant `docs/contracts/` or `docs/domains/` page
- `docs/workflows/TASK_AUTHORING.md`
- task doc at `docs/tasks/<domain>/<scene_id>/<task_id>.md`

## Testing checklist (before commit)
1. Run test suite:

```bash
PYTHONPATH=. pytest -q
```

Run RLVR-local reward tests with both the repo root and `rlvr/` root on the
import path:

```bash
cd rlvr && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=..:. pytest tests/test_trace_reward.py tests/test_trace_validation.py -q
```

2. If task logic/prompt/render changed, regenerate task-review artifacts:

```bash
PYTHONPATH=. python scripts/run_task_review.py --tasks <task_id> --mode full --out-root review/task-reviews
```

Use `scripts/generate_task_samples.py` only for quick local smoke/debugging;
browser review artifacts come from `scripts/run_task_review.py`.

3. If build/validation code changed, run a build smoke test:

```bash
PYTHONPATH=. python scripts/build_dataset.py --config configs/examples/minimal_build.yaml
```

## Commit checklist
- [ ] Changes are deterministic for fixed seeds.
- [ ] Task enforces unique-answer-by-construction.
- [ ] Typed `answer_gt` and `annotation_gt` are emitted correctly.
- [ ] Prompt bundle and prompt-variant metadata are wired correctly.
- [ ] Tests pass locally.
- [ ] Samples regenerated for changed tasks (when applicable).
- [ ] Relevant docs updated in the same change.

## Commit style
1. Keep commits scoped to one coherent change.
2. Use imperative commit messages (for example: `Add geometry area value task`).
3. Avoid mixing unrelated refactors with feature/task changes.
