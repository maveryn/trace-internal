# games Finalization Review

Audit mode: issue-focused, no source/config/prompt/review-artifact changes, solve-rate ignored.

## Summary

- Active scenes: 52
- Active tasks: 170
- Release decision: `accepted_for_training`
- Scenes with findings: 0
- Tasks with findings: 0
- Issue counts: blocker=0, fix_before_calibration=0, release_cleanup=0, follow_up=0

## Domain Inputs Reviewed

- Domain doc: `docs/domains/games.md`
- Task docs: `docs/tasks/games/`
- Source: `trace/tasks/games/`
- Configs: `configs/domains/games/`
- Prompts: `prompts/games/`
- Review artifacts: `review/task-reviews/games/`
- Browser issue DB and manual non-solve-rate audit gates were inspected; solve-rate status was intentionally ignored.

## Scene Inventory

| Scene | Tasks | Source layout | Code audit | Taxonomy audit | Source tests |
| --- | ---: | --- | --- | --- | --- |
| `2048` | 3 | source_layout | True | True | True |
| `backgammon` | 3 | source_layout | True | True | True |
| `battleship` | 4 | source_layout | True | True | True |
| `bingo` | 4 | source_layout | True | True | True |
| `bowling` | 3 | source_layout | True | True | True |
| `brick_breaker` | 3 | source_layout | True | True | True |
| `bubble_shooter` | 4 | source_layout | True | True | True |
| `cards` | 10 | source_layout | True | True | True |
| `checkers` | 4 | source_layout | True | True | True |
| `chess` | 8 | source_layout | True | True | True |
| `chess_variant` | 2 | source_layout | True | True | True |
| `circular_chess` | 2 | source_layout | True | True | True |
| `connect_four` | 4 | source_layout | True | True | True |
| `counterfactual_board` | 2 | source_layout | True | True | True |
| `crossing` | 3 | source_layout | True | True | True |
| `darts` | 3 | source_layout | True | True | True |
| `dominoes` | 6 | source_layout | True | True | True |
| `dots_and_boxes` | 3 | source_layout | True | True | True |
| `go` | 3 | source_layout | True | True | True |
| `hex` | 3 | source_layout | True | True | True |
| `irregular_link_board` | 2 | source_layout | True | True | True |
| `lane_runner` | 2 | source_layout | True | True | True |
| `ludo_board` | 3 | source_layout | True | True | True |
| `mancala_pit_board` | 3 | source_layout | True | True | True |
| `marble_chain` | 3 | source_layout | True | True | True |
| `match3` | 3 | source_layout | True | True | True |
| `minecraft` | 3 | source_layout | True | True | True |
| `minesweeper` | 3 | source_layout | True | True | True |
| `minigolf` | 2 | source_layout | True | True | True |
| `nine_mens_morris` | 2 | source_layout | True | True | True |
| `pacman` | 3 | source_layout | True | True | True |
| `pinball_table` | 2 | source_layout | True | True | True |
| `platformer` | 3 | source_layout | True | True | True |
| `pool` | 2 | source_layout | True | True | True |
| `racing_track` | 2 | source_layout | True | True | True |
| `radial_hunt_board` | 2 | source_layout | True | True | True |
| `reversi` | 3 | source_layout | True | True | True |
| `rhythm` | 4 | source_layout | True | True | True |
| `rule_override_board` | 2 | source_layout | True | True | True |
| `sixteen_soldiers` | 2 | source_layout | True | True | True |
| `sliding_block` | 4 | source_layout | True | True | True |
| `slot_machine` | 3 | source_layout | True | True | True |
| `snake` | 3 | source_layout | True | True | True |
| `snakes_ladders` | 3 | source_layout | True | True | True |
| `sokoban` | 3 | source_layout | True | True | True |
| `solitaire` | 5 | source_layout | True | True | True |
| `space_shooter` | 5 | source_layout | True | True | True |
| `tetris` | 5 | source_layout | True | True | True |
| `tic_tac_toe_3d` | 3 | source_layout | True | True | True |
| `tower_defense` | 3 | source_layout | True | True | True |
| `tower_draughts_board` | 2 | source_layout | True | True | True |
| `ultimate_tictactoe` | 3 | source_layout | True | True | True |

## Findings

No worthwhile finalization issues were found by this static/report-artifact pass.

## Duplicate / Split / Delete Candidates

No exact same-scene duplicate-contract candidates were found by the static scan. See `duplicate_candidate_scan.md` for closest-neighbor context.

## Generated Supporting Files

- `issues.md`
- `scene_inventory_snapshot.json`
- `task_signature_matrix.csv`
- `duplicate_candidate_scan.md`

## Validation Remaining

Run repo-level doc/inventory checks after all domain reports are written. No solve-rate validation is in scope for this pass.
