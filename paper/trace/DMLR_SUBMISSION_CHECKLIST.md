# DMLR Submission Checklist

This is a concise working checklist distilled from the official
[DMLR acceptance criteria](https://data.mlr.press/acceptance-criteria) and
[submission instructions](https://data.mlr.press/submissions.html), retrieved
2026-07-14. Recheck the live pages before submission.

## Scope and contribution

- [ ] Frame Trace as a data-centric contribution: a task environment, data
      generator, taxonomy, verifier architecture, and RLVR resource.
- [ ] State the scientific questions and contributions precisely.
- [ ] Show why the environment is useful beyond its raw scale.
- [ ] Compare against the closest dataset, benchmark-generator, and visual-RL
      work.

## Evidence and reproducibility

- [ ] Every claim has a clear evidence chain.
- [ ] The method, generator, task taxonomy, and evaluation protocol are
      reproducible from released artifacts.
- [ ] Dataset access URL and code URL are stable and public by publication.
- [ ] Record the exact release commit, dataset revision, seeds, model versions,
      hardware, decoding settings, and reward definitions.
- [ ] Report limitations, negative results, and uncertainty honestly.
- [ ] Provide enough documentation for intended use and extension.

## Dataset and artifact responsibilities

- [ ] Include a supplemental dataset document/data card.
- [ ] State data provenance, licenses, rights, privacy considerations, and
      author responsibility for distribution.
- [ ] State intended and out-of-scope uses.
- [ ] State hosting, versioning, maintenance, and long-term availability plans.
- [ ] Document known biases, renderer artifacts, coverage gaps, and misuse
      risks.
- [ ] Include checksums or immutable revisions for release artifacts.

## Manuscript requirements

- [ ] Use the official DMLR LaTeX style without changing margins or layout.
- [ ] Keep the paper self-contained and clearly written. DMLR currently states
      no page limit, but concision still matters.
- [ ] Include the required Broader Impact statement with tangible positive and
      negative consequences.
- [ ] Include funding, acknowledgements, and competing-interest disclosures.
- [ ] Place appendices after the references in the submitted manuscript.
- [ ] Verify citation completeness and link accessibility.
- [ ] Confirm current single-blind/OpenReview metadata requirements before
      submission.

## Trace-specific release gate

- [ ] Registry-derived counts match the release commit.
- [ ] Dataset manifests match paper counts and splits.
- [ ] All result tables are generated, not manually transcribed.
- [ ] The answer-only RLVR protocol and reward metrics are defined consistently
      in code, data, and paper.
- [ ] The public repository can generate a documented smoke dataset from a
      clean environment.
- [ ] The paper, public repository, dataset card, and model cards use the same
      terminology and version names.
