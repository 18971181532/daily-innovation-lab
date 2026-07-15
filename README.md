# Daily Innovation Lab

Small, tested, AI-assisted experiments exploring useful and playful software
ideas. Each project includes runnable code, documentation, validation, and a
clear disclosure of AI assistance.

## Projects

- **2026-07-15 — [Anime Arc Architect](projects/2026-07-15-anime-arc-architect/):** a stateful 12-episode anime season planner with character balancing, relationship evolution, plot-thread payoff, Markdown/JSON exports, and an SVG tension curve.
- **2026-07-13 — Text Constellation:** a deterministic text-to-SVG visual fingerprint generator (the root-level Python project below).

---

## Text Constellation

Turn a sentence into a deterministic constellation image. The same words always
produce the same stars, connections, color palette, and compact hexadecimal
seed—making the result useful as a visual fingerprint for notes, releases, or
small creative coding experiments.

![Example constellation](examples/curiosity.svg)

## Why it is interesting

- Deterministic output built from a SHA-256 text seed.
- A nearest-neighbor graph creates recognizable constellation structures.
- Generates a self-contained SVG with no third-party packages.
- Escapes user text safely before embedding it in XML.

## Run it

Python 3.10 or newer is recommended.

```bash
python constellation.py "Curiosity builds constellations" --output my-sky.svg
```

Choose between 5 and 200 stars:

```bash
python constellation.py "A small idea, carefully tested" --points 42
```

## Test it

```bash
python -m unittest discover -s tests -v
```

## Project note

This project was created with AI assistance as part of a transparent daily
creative-coding practice. Tests and reproducible output are included so the
result can be inspected rather than treated as a black box.
# Text Constellation

Turn a sentence into a deterministic constellation image. The same words always
produce the same stars, connections, color palette, and compact hexadecimal
seed—making the result useful as a visual fingerprint for notes, releases, or
small creative coding experiments.

![Example constellation](examples/curiosity.svg)

## Why it is interesting

- Deterministic output built from a SHA-256 text seed.
- A nearest-neighbor graph creates recognizable constellation structures.
- Generates a self-contained SVG with no third-party packages.
- Escapes user text safely before embedding it in XML.

## Run it

Python 3.10 or newer is recommended.

```bash
python constellation.py "Curiosity builds constellations" --output my-sky.svg
```

Choose between 5 and 200 stars:

```bash
python constellation.py "A small idea, carefully tested" --points 42
```

## Test it

```bash
python -m unittest discover -s tests -v
```

## Project note

This project was created with AI assistance as part of a transparent daily
creative-coding practice. Tests and reproducible output are included so the
result can be inspected rather than treated as a black box.
