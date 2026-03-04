# TRACE New Task Quickstart

## Goal
Add a new grounded task with:
1. deterministic generation,
2. typed answer + typed evidence,
3. external prompt templates,
4. trace payload metadata,
5. tests and sample artifacts.

## 0) Setup
Run from repo root:

```bash
cd /home/jovyan/work/trace
pip install -r requirements.txt
```

## 1) Create task module and register it
Create a new task file:
1. `trace/tasks/<domain>/<task_group>/<task_name>.py`

Import and register in:
1. `trace/tasks/__init__.py`

Minimal task skeleton:

```python
from __future__ import annotations

from typing import Any, Dict

from PIL import Image

from ....core.prompts import render_prompt
from ....core.seed import spawn_rng
from ....core.types import TaskComplexity, TypedValue
from ...base import TaskOutput
from ...registry import register_task


@register_task
class ExampleTask:
    task_id = "example_task"
    domain = "geometry"
    task_group = "measurement"

    @staticmethod
    def supported_query_types(_params: Dict[str, Any] | None = None):
        return ["default"]

    def generate(self, instance_seed: int, *, params: Dict[str, Any], max_attempts: int) -> TaskOutput:
        rng = spawn_rng(instance_seed, "scene")
        _ = rng  # replace with real deterministic generation

        prompt_result = render_prompt(
            domain=self.domain,
            task_group=self.task_group,
            bundle_id="example_bundle_v1",
            task_type_key="example_task_type",
            query_type=str(params.get("query_type", "default")),
            slots={"candidate_count": 3},
            instance_seed=instance_seed,
        )

        image = Image.new("RGB", (512, 512), (245, 245, 245))
        answer_gt = TypedValue(type="integer", value=1)
        evidence_gt = TypedValue(type="point_set", value=[[128.0, 128.0]])

        trace_payload = {
            "scene_ir": {"entities": []},
            "query_spec": {
                "query_type": str(params.get("query_type", "default")),
                "template_id": "example_task_v1",
                "prompt_variant": dict(prompt_result.metadata),
            },
            "render_spec": {"canvas_size": 512, "coord_space": "pixel"},
            "render_map": {"image_id": "img0", "anchors": {}},
            "execution_trace": {"answer": 1},
            "witness_symbolic": {"type": "id_set", "ids": ["entity_1"]},
            "projected_evidence": {"point_set": [[128.0, 128.0]]},
        }

        return TaskOutput(
            prompt=prompt_result.prompt,
            answer_gt=answer_gt,
            evidence_gt=evidence_gt,
            image=image,
            image_id="img0",
            image_rel_path=f"images/{self.domain}/{self.task_id}/{instance_seed}.png",
            trace_payload=trace_payload,
            complexity=TaskComplexity(
                complexity_score=0.25,
                complexity_components={"candidate_count": 3},
            ),
            task_versions={
                "dsl_spec_version": "v1",
                "template_version": "v1",
                "operator_bundle_version": "v1",
                "domain_capability_version": "v1",
                "renderer_version": "v1",
            },
            query_type=str(params.get("query_type", "default")),
        )
```

## 2) Add prompt bundle asset (no hardcoded prompt strings)
Create:
1. `prompts/<domain>/<task_group>/<bundle_id>.json`

Minimum schema:

```json
{
  "bundle_id": "example_bundle_v1",
  "schema_version": "v1",
  "task_type_templates": {
    "example_task_type": [
      "... 10+ variants ..."
    ]
  },
  "query_type_templates": {
    "default": [
      "... 10+ variants ..."
    ]
  },
  "required_slots_by_key": {
    "example_task_type": ["candidate_count"],
    "default": ["candidate_count"]
  }
}
```

## 3) Add/confirm task-group defaults
File:
1. `configs/task_groups/<domain>/<task_group>.yaml`

Confirm sections used by tasks:
1. `generation`
2. `rendering`
3. `prompt` (bundle/key defaults)
4. `visual.noise` (if noise is enabled)

## 4) Add tests
Create:
1. `tests/test_<task_id>.py`

Minimum tests:
1. deterministic generation for fixed seed,
2. answer/evidence consistency against execution trace,
3. prompt metadata presence (`trace_payload.query_spec.prompt_variant`),
4. build integration smoke with `BuildConfig`.

Run tests:

```bash
PYTHONPATH=. pytest -q
```

## 5) Add task documentation
Create:
1. `docs/tasks/<task_id>.md`

Start from template:

```bash
cp docs/tasks/TASK_DOC_TEMPLATE.md docs/tasks/<task_id>.md
```

Fill required sections:
1. prompt bundle id/key/query mapping,
2. required slot schema,
3. determinism + metadata details,
4. generation constraints (unique answer, reject/resample).

## 6) Generate review samples
Generate 50 samples for the task:

```bash
PYTHONPATH=. python scripts/generate_task_samples.py --tasks <task_id> --count 50 --clean
```

Outputs are written under:
1. `samples/<domain>/<task_group>/<task_id>/images/`
2. `samples/<domain>/<task_group>/<task_id>/data/`
3. `samples/<domain>/<task_group>/<task_id>/summary.json`
4. `samples/combined_samples.xlsx`

## 7) Run dataset build smoke test
Use existing example config or add one in `configs/examples/`.

```bash
PYTHONPATH=. python scripts/build_dataset.py --config configs/examples/minimal_build.yaml
```

## Done checklist
1. Task registered and import path wired.
2. No hardcoded prompt literals in task module.
3. Prompt bundle has 10+ variants for task and query templates.
4. Unique answer enforced by generation constraints.
5. Typed `answer_gt` and `evidence_gt` emitted.
6. Trace payload includes prompt metadata and projected evidence.
7. Tests pass.
8. Samples regenerated for changed task.
9. Task doc added/updated.
