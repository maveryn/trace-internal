# Trace Brand Assets

The Trace mark is a compact `3x3` atlas with a Trace monogram at its center.
Eight surrounding motifs summarize the eleven visual domains: games and
puzzles share the space-shooter tile; icons and symbolic tasks share the clock
tile; and illustrations and 3D scenes share an isometric-world tile. Charts,
geometry, graphs, pages, and physics retain dedicated motifs. This keeps the
mark legible while showing recognizable visual grammars rather than abstract
nodes. The game, isometric-world, and physics motifs derive from actual Trace
scene families.

## Files

- `trace-mark.svg`: standalone square mark for avatars, figures, and compact
  navigation.
- `trace-logo.svg`: horizontal mark and wordmark for repository and
  documentation headers.

Both files are transparent, self-contained SVGs. Their structural ink adapts
to the viewer's light or dark color preference. The standalone mark has no font
dependency. The horizontal wordmark uses a conventional sans-serif fallback
stack so it remains portable across browsers and document renderers.

## Palette

| Role | Hex |
|---|---|
| Structural ink | `#17242d` |
| Tile surface | `#f7f9f9` |
| Tile border | `#cad6da` |
| Secondary ink | `#667983` |
| Coral | `#e85d4a` |
| Gold | `#e5a62b` |
| Blue | `#3974d7` |
| Teal | `#159b91` |
| Space-scene lime | `#b9d63b` |
| Terrain green | `#56a45b` |
| Terrain edge | `#b9864f` |

Preserve the tile order, icon geometry, spacing, and palette in the primary
mark. For monochrome applications, all motifs may use one ink color, but the
atlas arrangement should remain unchanged.
