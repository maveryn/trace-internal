# Shared Visual Style Refactor Note

Purpose: capture the completed reusable non-semantic visual style families for
the synthetic 2D domains, plus the invariants future scene upgrades should keep.

## Completion Status

Status: complete for the eight domains that share 2D synthetic renderer style
families.

Implemented shared families:

- `panel_scene_style`: shared by `puzzles`, `games`, and `icons`.
- `technical_diagram_style`: shared by `geometry` and `physics`.
- `information_scene_style`: shared by `charts`, `pages`, and `graph`.

`illustrations` and `three_d` are intentionally outside this split. They need
asset/camera/scene-specific visual systems rather than these 2D background and
panel renderers.

Representative review artifacts regenerated during rollout:

- `plans/task-reviews/charts/single_series_chart/scene_review.xlsx`
- `plans/task-reviews/pages/sectioned_form/scene_review.xlsx`
- `plans/task-reviews/graph/node_link_graph/scene_review.xlsx`
- geometry/physics scene-review artifacts were regenerated during the
  technical-diagram rollout.

## Motivation

The current `agent_automaton_grid` pass showed that coupling treatment,
background color, accent color, cell palette, and marker colors into one fixed
`style_pack` limits visual variety. Future renderers should separate visual
structure from palette so each scene can sample more combinations while keeping
answer/evidence semantics unchanged.

## Proposed Axes

For panel-like synthetic scenes, split style into at least:

- `treatment`: layout/chrome/background texture family.
- `palette`: canvas, accent, cell/object, grid/stroke, marker, and text colors.

The current shared puzzle/game/icon panel renderer uses these 20 treatment ids:

- `bare_canvas`
- `plain_sheet`
- `matte_sheet`
- `thin_frame`
- `soft_panel`
- `margin_sheet`
- `dot_sheet`
- `worksheet_panel`
- `notebook_grid`
- `index_card`
- `clipboard_sheet`
- `printout_panel`
- `puzzle_card`
- `inset_board`
- `tabletop_mat`
- `corkboard_sheet`
- `game_table`
- `lab_panel`
- `arcade_screen`
- `terminal_screen`

The current shared palette ids are:

- `plain_neutral`
- `soft_gray`
- `warm_linen`
- `cool_blue`
- `slate_paper`
- `warm_paper`
- `gold_card`
- `rose_sheet`
- `violet_note`
- `cyan_lab`
- `mint_green`
- `teal_card`
- `sage_board`
- `coral_card`
- `sky_lilac`
- `arcade_navy`
- `arcade_purple`
- `terminal_green`
- `terminal_amber`
- `terminal_blue`

Palette is sampled independently where safe. Palettes declare compatibility as
`light`, `dark`, or `both`; dark treatments such as `arcade_screen` and
`terminal_screen` use dark-compatible palettes.

## Domain Style Families

Do not use one global renderer pass. Use shared style families plus
domain-specific adapters:

- `panel_scene_style`: puzzles, games, icons.
- `technical_diagram_style`: geometry, physics.
- `information_scene_style`: charts, pages, graph.
- asset/camera-specific styling: illustrations and 3D, tracked separately from
  these 2D shared renderer families.

The shared layer should own style IDs, palette sampling, contrast helpers, and
metadata schema. Each domain or scene still owns how style maps onto its own
geometry, evidence, and prompt contract.

For puzzles and games specifically, the panel-style implementation should be
shared, not copied. Treatments such as `plain_sheet`, `worksheet_panel`,
`puzzle_card`, `arcade_screen`, and `terminal_screen` should live once in the
shared panel-style layer and be reused by both domains. Puzzle and game modules
may provide thin adapters that map shared roles onto a board, option card, HUD,
rule card, token tray, or cell grid, but they should not reimplement separate
copies of the same treatment drawing code.

For geometry and physics, the technical-diagram implementation lives in
`trace/tasks/shared/visual_style/technical_diagram.py`. The domain adapters are
`trace/tasks/geometry/shared/diagram_style.py` and
`trace/tasks/physics/shared/diagram_style.py`. These adapters map shared roles
onto graph paper, axes, guide lines, labels, apparatus strokes, field-map
boards, and other math/physics diagram concepts. They must preserve
task-owned semantic colors and must not import the puzzle/game panel adapters.

The current technical-diagram treatment ids are:

- `bare_canvas`
- `off_white_paper`
- `graph_paper_light`
- `engineering_grid`
- `millimeter_paper`
- `blueprint_grid`
- `dark_blueprint`
- `lab_notebook`
- `ruled_notebook`
- `worksheet_panel`
- `textbook_figure`
- `presentation_slide`
- `whiteboard`
- `chalkboard_dark`
- `drafting_vellum`
- `isometric_grid`
- `subtle_scan_sheet`
- `exam_problem_box`
- `lab_card`
- `monochrome_print`

The current technical-diagram palette ids are:

- `neutral_ink`
- `cool_gray_blue`
- `warm_paper_ink`
- `graphite_blue`
- `engineering_cyan`
- `blueprint_white`
- `blueprint_amber`
- `lab_teal`
- `physics_orange`
- `geometry_indigo`
- `chalk_soft`
- `whiteboard_marker`
- `green_grid`
- `violet_annotation`
- `sepia_print`
- `slate_mint`
- `navy_lab`
- `steel_crimson`
- `olive_field`
- `magenta_cyan`

Technical diagrams also sample an independent frame mode, analogous to the
puzzle/game panel chrome mode but owned by the technical style family:

- `none` with default weight `0.5`
- `plain_outline` with default weight `0.25`
- `matching_outline` with default weight `0.25`

For charts, pages, and graph, the structured-information implementation lives
in `trace/tasks/shared/visual_style/information_scene.py`. The domain adapters
are `trace/tasks/charts/shared/information_style.py`,
`trace/tasks/pages/shared/information_style.py`, and
`trace/tasks/graph/shared/information_style.py`. These adapters map shared
roles onto chart axes/grid/text/surfaces, document page/field/value chrome, and
graph backgrounds/panels/connectors/labels while preserving semantic chart mark
colors, visible document values, graph topology, and task-owned color evidence.

The current information-scene treatment ids are:

- `clean_default`
- `report_card`
- `dashboard_tile`
- `executive_dashboard`
- `news_graphic`
- `academic_figure`
- `journal_appendix`
- `infographic_panel`
- `poster_explainer`
- `annotated_callout`
- `caption_heavy_figure`
- `source_note_sheet`
- `compact_small_multiples`
- `data_table_report`
- `web_article_embed`
- `desktop_app_window`
- `control_console`
- `presentation_slide`
- `print_scan_sheet`
- `dark_analytics_board`

The current information-scene palette ids are:

- `neutral_report`
- `publication_gray`
- `cool_business`
- `warm_editorial`
- `soft_mint`
- `slate_amber`
- `ink_teal`
- `burgundy_sage`
- `indigo_ochre`
- `coastal_blue`
- `atlas_map`
- `metro_bright`
- `data_viz_classic`
- `okabe_ito_light`
- `pastel_dashboard`
- `monochrome_news`
- `high_contrast_light`
- `dark_analytics`
- `dark_mint`
- `dark_blue_orange`

Information scenes also sample an independent chrome mode:

- `none` with default weight `0.5`
- `thin_frame` with default weight `0.25`
- `accent_frame` with default weight `0.25`

## Suggested Code Shape

Implementation target:

- Shared primitives under `trace/tasks/shared/visual_style/`.
  - `panel.py`: shared panel/canvas treatments for puzzles, games, and icons.
  - `palette.py`: reusable palette sampling and contrast validation.
  - `metadata.py`: shared trace/render metadata schema helpers.
  - `technical_diagram.py`: shared technical-diagram treatments, palettes,
    deterministic background rendering, protected-color filtering, contrast
    checks, and metadata for geometry/physics diagrams.
  - `information_scene.py`: shared structured-information treatments,
    palettes, deterministic background rendering, protected-color filtering,
    contrast checks, metadata, and disabled-by-default context text policy for
    charts/pages/graph.
- Domain adapters such as:
  - `trace/tasks/puzzles/shared/scene_style.py`
  - `trace/tasks/games/shared/scene_style.py`
  - `trace/tasks/icons/shared/scene_style.py`
  - `trace/tasks/geometry/shared/diagram_style.py`
  - `trace/tasks/physics/shared/diagram_style.py`
  - `trace/tasks/charts/shared/information_style.py`
  - `trace/tasks/pages/shared/information_style.py`
  - `trace/tasks/graph/shared/information_style.py`

Reusable treatment and palette pieces should live in the global shared visual
style layer. Domain-specific files such as `puzzles/shared/scene_style.py` and
`games/shared/scene_style.py` should remain adapters over that implementation.
When new game or puzzle scenes adopt these treatments, they should call the same
shared panel functions rather than adding parallel domain-local copies.

## Invariants

- Style choices are non-semantic unless a task explicitly queries them.
- Do not correlate treatment or palette with answer value, correct option,
  query id, or difficulty bucket unless explicitly intended and documented.
- Preserve prompt wording independence from sampled color names unless the task
  explicitly uses named colors.
- Record treatment, palette id, concrete RGB values, contrast/separation checks,
  canvas style, and any style-specific line/stroke settings in render metadata.
- Validate contrast after sampling; resample or fall back if a palette would
  hide cells, labels, markers, paths, pipes, pieces, or evidence-bearing items.
- Evidence bboxes/points must be computed after final layout, unit-size jitter,
  and style-dependent geometry are resolved.

## Current Agent Automaton Status

The current `agent_automaton_grid` renderer uses the global shared panel-style
layer through the puzzle adapter. Treatment and palette are separate axes, and
plain-ish background options include `bare_canvas`, `plain_sheet`,
`matte_sheet`, `thin_frame`, `soft_panel`, `margin_sheet`, and `dot_sheet`.
Future puzzle/game scenes should reuse this same global layer instead of adding
scene-local copies.
