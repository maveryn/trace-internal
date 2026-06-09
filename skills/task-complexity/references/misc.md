# Misc Complexity

Use the same small shared vocabulary unless a renderer family needs a documented extension:

- `visual_scan`
- `reasoning_load`
- `scene_variant_load`

Guidance:
1. Keep complexity within-task only. Do not compare misc scores against other domains.
2. Clock tasks should usually rise with minute-grid difficulty, hand-angle separation, offset size, direct-readout versus transformed readout, and visual clutter that affects clock-hand reading.
3. Automaton tasks should usually rise with grid/tape size, visible rule-table size, simulated step count, and scope size for marked-region counts.
4. Music-notation tasks should usually rise with the number of notes/symbols, staff density, accidental/key-signature burden, and whether the query requires interval, transposition, harmony, or rhythm reasoning.
5. Organic-structure tasks should usually rise with bond count, branch/ring count, overlapping structures, and how many target witnesses must be found.
6. Dice and spinner probability tasks should usually rise with sample-space size, number of attributes in the event, and whether the query uses conjunction, disjunction, thresholding, pairing, or conditioning.
7. Use `scene_variant_load` only when the task genuinely supports multiple visible scene grammars inside the same task.
