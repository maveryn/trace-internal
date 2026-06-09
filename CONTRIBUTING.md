# Contributing to TRACE

## Purpose
This file is the short developer workflow and pre-commit checklist for day-to-day contributions.

## Development workflow
1. Start from repo root and install dependencies:

```bash
pip install -r requirements.txt
```

2. Implement focused changes in the correct locations:
- task code: default `trace/tasks/<domain>/<task_group>/<task_name>.py`; tile exception `trace/tasks/tile/<task_group>_<task_name>.py`
- prompt bundles: `prompts/<domain>/<task_group>/`
- task-group config: `configs/domains/<domain>/<task_group>.yaml`
- task docs: `docs/tasks/<task_id>.md`

3. Reuse shared helpers before adding task-local utilities:
- `trace/core/`
- `trace/tasks/<domain>/shared/`
- `docs/workflows/SHARED_UTILITIES.md`

4. Follow code documentation standards while implementing:
- `docs/workflows/CODE_DOCUMENTATION.md`

5. Keep prompts externalized (no hardcoded prompt strings in task modules).

6. Update docs when behavior/contracts change:
- `docs/project/STATUS.md`
- `docs/project/TODO.md`
- `docs/workflows/TASK_AUTHORING.md`
- task doc under `docs/tasks/`

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
- [ ] Typed `answer_gt` and `annotation_gt` are emitted correctly.
- [ ] Prompt bundle and prompt-variant metadata are wired correctly.
- [ ] Tests pass locally.
- [ ] Samples regenerated for changed tasks (when applicable).
- [ ] Relevant docs updated in the same change.

## Commit style
1. Keep commits scoped to one coherent change.
2. Use imperative commit messages (for example: `Add geometry area value task`).
3. Avoid mixing unrelated refactors with feature/task changes.
