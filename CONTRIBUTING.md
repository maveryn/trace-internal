# Contributing to TRACE

## Purpose
This file is the short developer workflow and pre-commit checklist for day-to-day contributions.

## Development workflow
1. Start from repo root:

```bash
cd trace
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Implement focused changes in the correct locations:
- task code: `trace/tasks/<domain>/<task_group>/`
- prompt bundles: `prompts/<domain>/<task_group>/`
- task-group config: `configs/task_groups/<domain>/<task_group>.yaml`
- task docs: `docs/tasks/<task_id>.md`

4. Reuse shared helpers before adding task-local utilities:
- `trace/core/`
- `trace/tasks/<domain>/shared/`
- `docs/SHARED_UTILITIES.md`

5. Follow code documentation standards while implementing:
- `docs/CODE_DOCUMENTATION.md`

6. Keep prompts externalized (no hardcoded prompt strings in task modules).

7. Update docs when behavior/contracts change:
- `docs/STATUS.md`
- `docs/TODO.md`
- `docs/TASK_AUTHORING.md`
- task doc under `docs/tasks/`

## Testing checklist (before commit)
1. Run test suite:

```bash
PYTHONPATH=. pytest -q
```

2. If task logic/prompt/render changed, regenerate task samples:

```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks <task_id> --count 50 --clean
```

3. If build/validation code changed, run a build smoke test:

```bash
PYTHONPATH=. python scripts/build_dataset.py --config configs/examples/minimal_build.yaml
```

## Commit checklist
- [ ] Changes are deterministic for fixed seeds.
- [ ] Task enforces unique-answer-by-construction.
- [ ] Typed `answer_gt` and `evidence_gt` are emitted correctly.
- [ ] Prompt bundle and prompt-variant metadata are wired correctly.
- [ ] Tests pass locally.
- [ ] Samples regenerated for changed tasks (when applicable).
- [ ] Relevant docs updated in the same change.

## Commit style
1. Keep commits scoped to one coherent change.
2. Use imperative commit messages (for example: `Add geometry area value task`).
3. Avoid mixing unrelated refactors with feature/task changes.
