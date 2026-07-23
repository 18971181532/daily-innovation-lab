# Daily Innovation Lab

Small, tested, AI-assisted experiments exploring useful and playful software
ideas. Each project includes runnable code, documentation, validation, and a
clear disclosure of AI assistance.

## Projects

- **2026-07-15 — [Anime Arc Architect](projects/2026-07-15-anime-arc-architect/):** a stateful 12-episode anime season planner with character balancing, relationship evolution, plot-thread payoff, Markdown/JSON exports, and an SVG tension curve.
- **2026-07-13 — Text Constellation:** a deterministic text-to-SVG visual fingerprint generator (the root-level Python project below).

---

## Text Constellation · v0.2

Turn a sentence into a deterministic constellation image. The same words always
produce the same stars, connected graph, color palette, compact hexadecimal
fingerprint, and analysis manifest—making the result useful as a visual identity
for notes, releases, or small creative-coding experiments.

![Example constellation](examples/curiosity.svg)

### What changed in v0.2

- **Guaranteed connectivity:** a deterministic minimum-spanning backbone makes
  every star reachable, while local nearest-neighbour edges add character.
- **Explainable output:** an optional JSON manifest reports graph density,
  average and maximum degree, edge lengths, palette, and fingerprint.
- **Three seeded themes:** `aurora`, `ember`, and `nebula`; `auto` selects one
  reproducibly from the input text.
- **Accessible SVG:** the self-contained image now has an explicit title,
  description, role, responsive sizing, embedded metadata, and stable
  `data-*` identifiers.
- **Privacy-aware manifest:** analysis metadata contains the fingerprint and
  structure, but does not repeat the source phrase.

The implementation still uses only the Python standard library.

### Run it

Python 3.10 or newer is recommended.

```bash
python constellation.py "Curiosity builds constellations" --output my-sky.svg
```

Choose between 5 and 200 stars:

```bash
python constellation.py "A small idea, carefully tested" --points 42
```

Choose a palette and write a machine-readable analysis sidecar:

```bash
python constellation.py "A connected idea" \
  --theme nebula \
  --points 48 \
  --output connected-idea.svg \
  --manifest connected-idea.json
```

The manifest is useful for release automation or comparing visual fingerprints:

```json
{
  "fingerprint": "57180f78edf99b61",
  "theme": "nebula",
  "graph": {
    "connected": true,
    "stars": 32,
    "backbone_edges": 31
  }
}
```

See [the algorithm note](docs/text-constellation-algorithm.md) for the graph
construction, reproducibility contract, complexity, and metadata definitions.

### Test it

```bash
python -m unittest discover -s tests -v
```

### Project note

This project was created with AI assistance as part of a transparent daily
creative-coding practice. Tests and reproducible output are included so the
result can be inspected rather than treated as a black box.
