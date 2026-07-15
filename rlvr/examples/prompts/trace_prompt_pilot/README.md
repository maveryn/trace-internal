# Trace System Prompt Pilot Variants

These prompts are inactive pilot assets for comparing Trace answer-mode and
answer-and-annotation-mode behavior. They do not change the active default
prompt wiring.

Use `ALL_PROMPTS.txt` to inspect the six Trace pilot prompts in one place.

## Prompt Files

Answer mode:

- `answer_short_json_tail.txt`
- `answer_detailed_json_tail.txt`
- `answer_detailed_answer_tag.txt`

Answer-and-annotation mode:

- `answer_and_annotation_short_json_tail.txt`
- `answer_and_annotation_detailed_json_tail.txt`
- `answer_and_annotation_detailed_answer_tag.txt`

Reference only:

- `vero_training_system_prompt_reference.txt` is a local reference copy of the
  Vero training system prompt from
  `/home/jovyan/work/vero/vero-rl/examples/prompts/system_prompt_chatting.txt`.
  It is not Trace-compatible as-is because it uses boxed answers instead of
  Trace JSON.
