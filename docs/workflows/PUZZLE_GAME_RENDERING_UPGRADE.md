# Puzzle And Game Rendering Upgrade Checklist

Use this checklist when upgrading puzzle and game scenes with repeated boards,
cells, tiles, stickers, voxels, or similar units. The goal is more visual
variety without changing task semantics, evidence contracts, or verifier
payloads.

## Scope

Apply this workflow scene by scene to puzzle and game renderers that use:

- square grid cells, tiles, board squares, maze cells, pipe cells, word-search
  cells, nonogram cells, Sokoban cells, Star Battle/Tents cells, or automaton
  cells
- game board squares, card/tableau slots, lane segments, HUD panels, candidate
  move panels, or option cards
- cube/voxel units, Rubik stickers, polyomino cells, match-3 gems, marble-chain
  tokens, or other repeated visual units

Do not use a broad global decorative layer. Prefer scene-specific style packs
that understand the scene geometry.

Cell-backed boards are the `puzzles/cell_board` scene. Their implementation,
configs, and prompt bundles live under the puzzles domain paths.

## Preflight Rules

- Treat these upgrades as render-only unless a scene-specific issue explicitly
  requires a semantics change.
- Keep answer distributions, solver logic, verifier contracts, and task
  semantics unchanged.
- Project public evidence after the final unit size, layout placement, and
  canvas size are sampled.
- Keep effective visible unit size `>= 28px`. Aim for a `2x` min-to-max
  unit-size span first, but `2x` is a target rather than a hard rule; use a
  narrower documented range when readability, fit, or evidence integrity would
  otherwise suffer.
- Random placement must stay inside safe bounds. If the board or panel fills
  the canvas, record the zero-slack case instead of adding artificial movement.
- Preserve semantic contrast. Do not add palettes or style packs that make
  required classes, pieces, markings, words, paths, pipes, stickers, or cells
  harder to distinguish.
- Use the shared role-aware font dispatcher. Board labels, option labels,
  badges, HUD text, and other read-required text use `role="readout"`;
  non-answer chrome/context text may use `role="context"`; purely decorative
  visual dressing may use `role="decorative"`. Record the resolved family,
  role, pool id, pool size, and asset version in render metadata.
- Keep font choice consistent inside one board, card/tableau group, option
  set, or puzzle panel unless mixed typography is an intentional part of the
  scene grammar.
- Upgrade one scene at a time, regenerate the scene review artifacts, inspect
  them in the browser review app, and then move to the next scene.
- Do not run solve-rate jobs unless explicitly requested.

## Style Variation Ownership

- Define broad reusable style primitives at the domain level: background/tint
  families, neutral palette ranges, noise defaults, style-pack schema, and
  seeded sampling helpers.
- Apply style variation at the scene level by default. Each scene renderer owns
  how those primitives map to board/cell colors, grid strokes, unit-size jitter,
  canvas slack, option cards, labels, rule cards, pieces, tokens, stickers, or
  other visible elements.
- Puzzle/game scenes that adopt the global panel-style layer should draw from
  the shared 20-treatment / 20-palette registry in
  `trace/tasks/shared/visual_style/` instead of creating scene-local treatment
  or palette copies.
- Game-domain scenes should also aim for at least five scene-local
  board/object style variants in addition to shared background/panel/font
  variation. These style variants should affect the game artifact itself,
  such as board skins, tile palettes, piece/token treatments, grid/line
  strokes, card/table chrome, lane skins, or HUD/control styling.
- Fewer than five scene-local game styles is allowed only when the canonical
  game artifact or readability constraints make extra styles unsafe; document
  the exception in the game-domain setup doc and record the active style axis
  in render metadata.
- Do not add a broad domain-level renderer pass that blindly recolors or moves
  repeated-unit scenes. A style that is safe for one scene can break semantic
  contrast, evidence projection, or readability in another.
- Scene-level style sampling must be recorded in render metadata and must not
  correlate with query type, answer value, correct option, or difficulty bucket
  unless explicitly intended and documented.

## Required Checks

### 1. Effective Unit Size

- Define the scene's repeated unit explicitly: grid cell, board square, tile,
  sticker, voxel face, maze cell, pipe cell, gem, or equivalent.
- Enforce effective visible unit size `>= 28px` after jitter/scale. For
  non-square or projected units, use the smaller visible dimension.
- Try to keep the min-to-max unit-size range at least `2x`. If that crowds the
  scene or hurts readability/evidence integrity, use the largest safe range and
  document the reason.
- Record the effective unit-size metadata in `render_spec`, such as
  `unit_size_jitter`, `voxel_scale`, or a scene-specific equivalent.

### 2. Layout Placement

- Compute board/content size before choosing the board position.
- Randomly place the board or main panel inside safe canvas bounds.
- Prefer fractional slack-based placement jitter: resolve the content size first,
  compute the safe free space on each side, then sample an offset as a fraction
  of that available slack. Small fixed pixel offsets are usually not enough to
  visibly move board-inside-canvas scenes.
- If the scene nearly fills the canvas and the valid offset range is zero,
  record that explicitly in layout metadata; this is acceptable.
- Do not translate/crop rendered pixels after drawing unless every entity bbox,
  evidence bbox, and trace coordinate is transformed identically.
- Record `layout_jitter` with final panel/board origin, available offset range,
  content size, and canvas size.

### 3. Dynamic Canvas Size

- Avoid small boards floating in a large fixed canvas.
- Let canvas size follow the resolved content footprint plus bounded slack.
- Keep enough slack for visible placement variation when feasible.
- Preserve readable margins, option labels, coordinate labels, and evidence
  boxes.
- Watch image-token/prompt-token pressure for large boards and option-heavy
  scenes.

### 4. Evidence Integrity

- Evidence and answer must come from the same final layout coordinates.
- All evidence-bearing bboxes must stay inside the final canvas.
- Decorative chrome must not be included as evidence unless the task explicitly
  asks about it.
- Style, placement, palette, and layout choices must not create alternative
  valid answers or hide required evidence.

### 5. Style Packs

- Add scene-specific style packs, not one-size-fits-all ornamentation.
- Cover the full visual surface that matters for inspection: backgrounds,
  palettes, panels/chrome, grid or board strokes, unit sizes, marker styles,
  piece/token styles, board skins, option cards, and label/badge treatments.
  A scene is not visually upgraded just because the canvas background changes.
- Puzzle style examples: contest worksheet, notebook, puzzle magazine, scanned
  puzzle page, option sheet, lab/grid board, paper card.
- Game style examples: tabletop board, arcade HUD, score strip, move-history
  strip, short rule card, candidate-move panel, compact game UI frame.
- Keep wrappers non-semantic unless the task explicitly asks about a UI/rule
  element.
- Long instruction text should not become OCR source of truth. Keep visible rule
  cards short and metadata-grounded.

### 6. Color And Contrast

- Add multiple board palettes and grid/line styles where safe.
- Maintain contrast for:
  - letters, numbers, and coordinate labels
  - grid lines, walls, paths, pipes, and board boundaries
  - answer options and selected/marked cells
  - game pieces, stickers, tokens, and highlights
- Color palettes, style packs, and chrome variants must not correlate with
  query type, answer value, correct option, or difficulty bucket unless
  explicitly intended and documented.

### 7. Metadata

Record enough metadata to debug and audit the rendered scene:

- `style_pack` or scene-variant name
- board/cell palette id or explicit RGB values
- grid/line/stroke style and widths
- effective unit size and unit-size range
- `layout_jitter` and final canvas size
- main board/panel bbox and content bbox
- post-image noise/background metadata

## Scene Review Procedure

For each scene:

1. Inspect current renderer and configs for fixed origins, fixed canvas sizes,
   narrow palettes, and unit sizes below 28px.
2. Implement the smallest scene-local change that fixes one issue class.
3. Compile touched modules.
4. Smoke-generate multiple seeds and verify:
   - effective unit size is never below 28px
   - `2x` unit-size variation is attempted first, or a narrower safe range is
     documented
   - board/panel origin varies when there is slack
   - canvas follows content size
   - evidence bboxes remain inside the canvas
   - style variants are visible but non-semantic
5. Regenerate the scene review artifacts and inspect them in the browser app.
6. Do not run solve-rate jobs unless explicitly requested.

## Coverage-Extension Notes

The puzzle coverage plan notes that benchmark puzzle images often look like
contest workbook panels, game UI screens, labeled option sheets, or scanned
puzzle pages. It also warns that puzzle geometry is sensitive: style wrappers
must not alter grid coordinates, option geometry, maze topology, cube geometry,
fold/overlay coordinates, word-grid cells, or evidence semantics.

The games coverage plan notes that benchmark game images often include game-like
UI framing, answer options, coordinate labels, state panels, rule cards, score
strips, move-history boxes, and HUD elements. Add these only when they do not
alter board geometry, evidence bboxes, rule semantics, or visible
cell/piece readability.
