# Trace Paper Roadmap

Sections 3 and 4 contain the executable-instance formalism, program-centered
taxonomy, worked task boundaries, and method figures. The remaining work is to
bind the frozen release and answer-only RLVR experiments to canonical evidence,
then complete the results and final prose.

## 1. Paper thesis

Trace is a taxonomy-guided environment for multidomain visual reasoning. Its
central contribution is a task design and generation system in which:

1. the public taxonomy separates visible scene grammar (`scene_id`) from a
   stable reasoning contract (`task_id`);
2. every task has an executable program, typed answer, and explicit verifier
   contract;
3. instances are deterministic, replayable, and generated with controlled
   visual and semantic variation; and
4. the resulting task distribution supports broad answer-based RLVR.

The paper should lead with the environment design. Dataset scale and RLVR
results validate that design; they do not replace the taxonomy or generation
story. Trace also retains optional image-space annotations for task auditing,
but annotation supervision is not a primary claim or experiment in this report.
Difficulty calibration remains a repository development workflow and is not a
main-paper contribution; mention it only in an appendix if it supports a
reported analysis.

## 2. Verified inventory

The active registry currently contains:

- **1,000 tasks**
- **277 scenes**
- **11 domains**

These values were recomputed from the active task registry on 2026-07-14.
Before release, generate the inventory table directly from the registry and
record its hash in `provenance/README.md`.

Current task counts by domain are: charts 180, games 170, geometry 170, graph
60, icons 50, illustrations 60, pages 80, physics 50, puzzles 60, symbolic 60,
and three-dimensional scenes 60. The final table must be generated rather than
manually transcribed.

## 3. Contribution hierarchy

The introduction should make at most four top-level claims:

1. **A principled task taxonomy.** Trace separates domain, scene grammar,
   objective contract, and internal query variation using executable program
   boundaries rather than prompt names.
2. **Executable and verifiable generation.** Answers are computed from latent
   scene state and packaged with typed reward contracts and replayable traces.
3. **Broad procedural coverage with explicit quality control.** The release
   covers 1,000 tasks across 277 scenes and 11 domains, with contract
   validation, manual review, and deterministic export.
4. **Evidence for post-training utility.** Controlled answer-only RLVR
   experiments measure transfer across a broad external benchmark suite.

Claim 4 must match the final canonical result artifacts. Do not include pending
or exploratory supervision variants in the abstract or contribution list.

## 4. Section roles

### Abstract and introduction

Use a direct sequence: problem, Trace design, verified scale, answer-only RLVR
setup, and one evidence-backed result. Motivate the need for stable task units,
executable answers, controlled rendering, and reproducible reward contracts.

### Related work

Organize by problem rather than chronology:

- controlled visual task generation;
- executable generator--verifier environments;
- open data for multimodal reinforcement learning;
- synthetic and verifiable visual RL data; and
- precise positioning of Trace.

Keep the section between 1.25 and 1.5 rendered pages. Do not create a dedicated
grounding or annotation-supervision subsection.

### The Trace environment

Describe the primary instance record as image, prompt, typed answer, reward
contract, and sidecar trace. Explain semantic generation, task execution,
rendering, prompt realization, verifier binding, and deterministic replay. The
reachable-region example should demonstrate that the answer and verifier state
come from one execution. Any projected overlay is explanatory audit metadata,
not a required training output.

### Program-centered taxonomy

This is the paper's main section. Explain:

- `domain -> scene_id -> task_id`;
- scene as visible input grammar;
- task as stable reasoning program plus answer and verifier contract;
- query as meaningful internal program or prompt variation, not a sampling
  unit;
- program canonicalization across scenes and domains; and
- the conservative split/merge policy through concrete examples.

### Generation and quality control

Describe task-level uniform sampling, versioned prompt assets, visual and
semantic variation, unique-answer construction, schema validation,
deterministic replay, manual review, and export.
Separate code-enforced guarantees from human review procedures.

### Experiments, results, and analysis

Define the frozen base model, dataset revision, answer-only RLVR recipe,
benchmark suite, decoding, and metrics. The primary comparison is base versus
Trace answer-only RLVR under a controlled protocol. Report aggregate and
per-benchmark results, then analyze transfer by task family, program breadth,
and synthetic-to-external generalization. Negative transfer must remain visible.

### Limitations and conclusion

Discuss taxonomy subjectivity, renderer regularities, synthetic-to-real
transfer, coverage gaps, verifier limits, compute, and maintenance. A brief
future-work note may mention learning from the audit annotations, but the
conclusion should return to taxonomy, generation, verification, and replay.

## 5. Required figures and tables

1. **Domain montage (complete):** representative images from all 11 domains.
2. **Executable instance pipeline (complete):** semantic execution, answer,
   verifier binding, replay trace, and typed reward.
3. **Task-boundary examples (complete):** query variation, task splitting, and
   non-query generation variation.
4. **Coverage summaries (complete):** generated domain, scene, task,
   answer-type, query-branch, and dominant-operation counts.
5. **Rendering variation (complete):** a fixed semantic instance under
   controlled theme, typography, layout, context, and raster changes.
6. **Main RLVR table (complete):** base, answer-trained, and contextual 7B
   checkpoints under one protocol.
7. **Transfer analysis (complete):** per-benchmark 3B and 7B deltas grouped by
   evaluation category.
8. **Ablations:** only completed experiments that share a controlled setup.

All numeric assets must be generated from canonical artifacts.

## 6. Evidence required before completion

Already available:

- active registry and task inventory;
- source contracts and domain/task documentation;
- review artifacts and build-validation records;
- registry-derived coverage summaries and generated method figures;
- frozen train/validation split and dataset manifests; and
- consolidated training provenance, base/answer-RLVR score records, generated
  result tables, and per-benchmark transfer figures.

Still required:

1. bind the final public release commit and stable repository/model links; and
2. complete the final arXiv source, accessibility, and claim audit.

## 7. Evidence and writing policy

Classify every claim as a contract fact, inventory fact, dataset fact,
experimental fact, interpretation, or planned work. Record each figure and
table's source files, commit, dataset revision, command, and output hash in
`provenance/README.md`.

Lead paragraphs with claims, then evidence and implications. Keep section roles
distinct. Prefer concrete terms such as scene grammar, objective contract,
execution trace, typed answer, and verifier contract. Do not describe scale as
quality, manually transcribe result cells, hide negative transfer, or present
planned experiments as completed.

## 8. Completion order

1. Freeze release identity and update the provenance ledger.
2. Generate inventory and coverage assets.
3. Finalize generation and quality-control prose from verified artifacts.
4. Lock the experimental protocol before editing results prose.
5. Generate tables and plots from canonical results.
6. Write results, analysis, limitations, and conclusion.
7. Finalize introduction and abstract last.
8. Run LaTeX, reference, figure, table, accessibility, and claim audits.

The paper is complete only when every TODO is resolved or deliberately removed
and every numeric claim has recorded provenance.
