# Changelog

All notable changes to Text Constellation are documented here.

## 0.2.0 — 2026-07-23

### Added

- A deterministic minimum-spanning backbone that guarantees a connected graph.
- Local nearest-neighbour edges that preserve the organic constellation shape.
- Reproducible `aurora`, `ember`, and `nebula` themes with an `auto` mode.
- JSON analysis manifests with graph and canvas statistics.
- Accessible SVG titles, descriptions, roles, embedded metadata, and stable IDs.
- Responsive standalone SVG sizing that preserves the full image on narrow screens.
- Regression coverage for graph connectivity, themes, XML validity, and privacy.

### Changed

- Long backbone edges are retained at low opacity instead of being discarded.
- The CLI now accepts canvas size, theme, and optional manifest arguments.
- The bundled example is regenerated with 32 stars and a `nebula` palette.
