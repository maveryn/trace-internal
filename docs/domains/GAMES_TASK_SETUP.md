# Games Task Setup

Use this document for the active `games` domain contract.

## 1) Domain scope
1. `games` should stay state-first: the image should depict a recognizable game artifact whose visible pieces are enough to solve the query.
2. Early games tasks should prefer low-convention counting/comparison questions over deep game-strategy or hidden-information rules.
3. Prompt-facing evidence should stay on the visible game pieces themselves (for example card boxes), not on decorative table chrome.

## 2) Active families
### `cards`
1. Active tasks:
   - `task_games_cards_hand_count`
2. `task_games_cards_hand_count` scene/query surface:
   - `scene_variant`: `single_row|two_row`
   - `query_variant`: `same_suit_as_reference_count|higher_than_reference_count|pair_count|longest_run_length`
3. `task_games_cards_hand_count` evidence contract:
   - unordered card `bbox_set` evidence over the relevant cards in the visible hand
4. `task_games_cards_hand_count` prompt policy:
   - use explicit rank-order text whenever the query depends on rank comparison or runs,
   - mark the reference card visually with `REF` when a query uses one,
   - keep pair semantics explicit as “rank appears exactly twice,”
   - when two rows are shown for ordered run reasoning, keep a visible continuation cue and mention the reading order in the prompt.

### `dominoes`
1. Active tasks:
   - `task_games_dominoes_chain_count`
2. `task_games_dominoes_chain_count` scene/query surface:
   - `scene_variant`: `single_row|two_row`
   - `query_variant`: `matching_end_count|higher_sum_than_reference_count|sum_to_target_count|double_count`
3. `task_games_dominoes_chain_count` evidence contract:
   - unordered loose-domino `bbox_set` evidence over the matching candidate tiles below the top chain
4. `task_games_dominoes_chain_count` prompt policy:
   - keep the count target explicitly on the loose dominoes below the chain rather than the top chain itself,
   - use a visible `REF` tag only when the chain provides a comparison tile,
   - explain connection, pip-sum, and double semantics directly in the prompt when the query depends on them,
   - keep the open-end cue visually strong when the query asks which loose tiles can extend the chain.

### `reversi`
1. Active tasks:
   - `task_games_reversi_move_count`
2. `task_games_reversi_move_count` scene/query surface:
   - `scene_variant`: `compact_board|classic_board`
   - `query_variant`: `legal_move_count|corner_move_count|flip_count_for_marked_move`
3. `task_games_reversi_move_count` evidence contract:
   - unordered board-square `bbox_set` evidence over either the legal destination squares or the discs that would flip for the marked move
4. `task_games_reversi_move_count` prompt policy:
   - explicitly name the current player,
   - explain the legal-move bracketing rule directly in the prompt,
   - keep the marked move visually obvious for flip-count queries without making it prompt-facing evidence.

### `connect_four`
1. Active tasks:
   - `task_games_connect_four_move_count`
2. `task_games_connect_four_move_count` scene/query surface:
   - `scene_variant`: `midgame_board|crowded_board`
   - `query_variant`: `winning_move_count|safe_move_count`
3. `task_games_connect_four_move_count` evidence contract:
   - unordered board-square `bbox_set` evidence over either immediate winning landing squares or safe landing squares
4. `task_games_connect_four_move_count` prompt policy:
   - explicitly name the current player,
   - explain the gravity/drop rule directly in the prompt,
   - explain the four-in-a-row win condition directly in the prompt,
   - define “safe move” directly in the prompt instead of assuming next-turn threat semantics are obvious.

### `checkers`
1. Active tasks:
   - `task_games_checkers_move_count`
2. `task_games_checkers_move_count` scene/query surface:
   - `scene_variant`: `midgame_board|crowded_board`
   - `query_variant`: `legal_move_count|capture_move_count`
3. `task_games_checkers_move_count` evidence contract:
   - unordered board-square `bbox_set` evidence over the landing squares of the counted moves
4. `task_games_checkers_move_count` prompt policy:
   - explicitly name the current player,
   - explain forward movement direction directly in the prompt instead of assuming board orientation conventions,
   - state that all shown pieces are ordinary men rather than kings,
   - state that captures are not mandatory for `legal_move_count`,
   - state that only the first jump counts for `capture_move_count`.

### `mancala`
1. Active tasks:
   - `task_games_mancala_move_count`
2. `task_games_mancala_move_count` scene/query surface:
   - `scene_variant`: `midgame_board|crowded_board`
   - `query_variant`: `extra_turn_move_count|capture_move_count`
3. `task_games_mancala_move_count` evidence contract:
   - unordered pit `bbox_set` evidence over the qualifying starting pits on Blue's bottom row
4. `task_games_mancala_move_count` prompt policy:
   - explicitly state that Blue controls the bottom row and the right store,
   - explain that sowing moves counterclockwise, includes Blue's store, and skips Orange's store,
   - define the extra-turn and capture rule directly in the prompt instead of assuming Mancala conventions,
   - keep evidence on the starting pits rather than on stores or implied landing pits.

## 3) V1 games-domain policy
1. Prefer one stable visible game scaffold per task id; widen question diversity through `task_variant` before splitting into more task ids.
2. Keep early tasks fully face-up and fully observable; do not require hidden cards or unstated game conventions.
3. When a query asks about an ordered sequence across wrapped rows, make the reading order explicit in both the image and the prompt.
4. Keep evidence local to the actual pieces that satisfy the queried predicate.

## 4) Active coverage snapshot
1. `cards`
   - `task_games_cards_hand_count`
2. `dominoes`
   - `task_games_dominoes_chain_count`
3. `reversi`
   - `task_games_reversi_move_count`
4. `connect_four`
   - `task_games_connect_four_move_count`
5. `checkers`
   - `task_games_checkers_move_count`
6. `mancala`
   - `task_games_mancala_move_count`

## 5) Shared helper placement
1. Cross-domain integer-support balancing now lives in `trace/tasks/shared/support_sampling.py`.
2. Games-domain visual defaults belong in `trace/tasks/games/shared/visual_defaults.py`.
3. Games-domain shared axis-sampling helpers belong in `trace/tasks/games/shared/sampling.py`.
4. Games-domain card/domino/Reversi/Connect Four/Checkers/Mancala theming belongs in `trace/tasks/games/shared/style.py`.
5. Games-domain card-hand rendering helpers belong in `trace/tasks/games/shared/card_scene.py`.
6. Games-domain domino-chain rendering helpers belong in `trace/tasks/games/shared/domino_scene.py`.
7. Games-domain Reversi rules helpers belong in `trace/tasks/games/shared/reversi_common.py`.
8. Games-domain Reversi board rendering helpers belong in `trace/tasks/games/shared/reversi_scene.py`.
9. Games-domain Connect Four rules helpers belong in `trace/tasks/games/shared/connect_four_common.py`.
10. Games-domain Connect Four board rendering helpers belong in `trace/tasks/games/shared/connect_four_scene.py`.
11. Games-domain Checkers rules helpers belong in `trace/tasks/games/shared/checkers_common.py`.
12. Games-domain Checkers board rendering helpers belong in `trace/tasks/games/shared/checkers_scene.py`.
13. Games-domain Mancala rules helpers belong in `trace/tasks/games/shared/mancala_common.py`.
14. Games-domain Mancala board rendering helpers belong in `trace/tasks/games/shared/mancala_scene.py`.
15. Games-domain normalized complexity helpers belong in `trace/tasks/games/shared/complexity.py`.
