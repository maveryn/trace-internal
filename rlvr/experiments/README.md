# RLVR Experiments

This directory records concrete RLVR training profiles that were run in TRACE.
Use these notes as machine/config references before starting similar EasyR1
jobs, then follow the active runbook for current launch procedure:

```text
docs/workflows/TRACE_ANNOTATION_ABLATION_RUNBOOK.md
```

Profiles:

- `h200_qwen25vl3b_easyr1_annotation.md` - 8x H200 settings used for
  Qwen2.5-VL-3B TRACE answer-and-annotation EasyR1 ablations.
- `annotation_system_prompt_response_length.md` - annotation-mode system prompt
  provenance and response-length behavior before and after the prompt update.
- `annotation_ablation_summary_20260713.md` - summary of completed 8x H200
  annotation reward and prompt ablations, plus the selected sectioned-reasoning
  follow-up run.
