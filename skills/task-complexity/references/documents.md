# Documents Complexity

Use a small shared vocabulary for early document tasks unless a broader family proves it needs more:

- `visual_scan`
- `reasoning_load`
- `scene_variant_load`

Guidance:
1. Keep complexity within-task only. Do not compare document scores against other domains.
2. For field-readout document tasks, `visual_scan` should usually rise with visible field count, page density, and whether the page grammar is multi-column or narrow and vertically dense.
3. Keep `reasoning_load` tied to the actual query burden inside the task:
   - direct field lookup is low,
   - longer visible values are slightly harder than short IDs,
   - contact and amount fields can be harder than compact identifiers when punctuation density increases.
   - section-local arithmetic queries should sit above readout and extremum tasks because the model must localize the named block, read multiple visible operand values, and compute the derived amount rather than selecting a visible winner.
   - section-membership layout queries should sit above plain readout but below arithmetic when they require localizing the correct named block from one field cue without any extra arithmetic or counting.
   - section-local extremum queries should rise above readout because the model must first locate the named block and then compare the visible values inside it.
   - section-local checkbox counts should sit between readout and extremum tasks: they still require finding the named block, but the local reasoning is a count over visible checked states rather than a value comparison.
4. Use `scene_variant_load` only when the same task genuinely supports multiple page grammars with different visual search burdens.
5. If a later document family uses only one stable page presentation, give `scene_variant_load` zero weight instead of inventing fake variation.
