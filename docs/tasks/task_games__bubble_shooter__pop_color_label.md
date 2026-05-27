# `task_games__bubble_shooter__pop_color_label`

## Contract
1. Domain: `games`
2. Task group: `bubble_shooter`
3. Scene id: `bubble_shooter`
4. Query id: `pop_color_label`
5. Objective: choose the labeled next-bubble color option that would make bubbles pop at the marked landing target.
6. Answer type: `string` option label.
7. Evidence type: `bbox_set` over the chosen option, the marked landing target, and the existing board bubbles that would pop.

## Generation Notes
1. The landing target is fixed; only the displayed option color varies.
2. Exactly one displayed option creates a same-color connected group of size at least three after placement.
3. The answer is the option label, not the color name.
4. The evidence is projected from the same computed popping group used for answer verification.
