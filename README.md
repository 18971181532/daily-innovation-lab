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
