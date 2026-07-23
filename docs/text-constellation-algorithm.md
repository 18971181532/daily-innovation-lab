# Text Constellation algorithm

Text Constellation v0.2 converts a phrase into two related artifacts:

1. an accessible, self-contained SVG image;
2. an optional JSON manifest describing the graph without repeating the phrase.

## Reproducibility contract

The first eight bytes of the phrase's SHA-256 digest form a 64-bit seed. That
seed drives star positions, radii, the automatic palette, and the hexadecimal
fingerprint. Identical text, dimensions, star count, and theme therefore
produce byte-identical SVG and JSON output.

Changing an explicit theme changes the palette but not the fingerprint or
geometry. Changing the text changes the seed and therefore the whole image.

## Connected graph construction

The original nearest-neighbour graph could split into disconnected islands.
Version 0.2 builds two edge layers:

### 1. Minimum-spanning backbone

Starting with star zero, the algorithm repeatedly adds the shortest edge from
the connected set to any unconnected star. This is Prim's algorithm. For `n`
stars it produces exactly `n - 1` backbone edges and guarantees that every star
is reachable from every other star.

### 2. Local detail

Each star then nominates its two nearest neighbours. Edges already present in
the backbone are ignored and the remaining unique pairs form a lighter local
layer. The result keeps the visual clusters of the first version without
sacrificing connectivity.

The implementation uses direct pairwise distances. With the CLI limit of 200
stars, the `O(n²)` time and memory-free distance calculation remain small and
easy to audit.

## Manifest fields

- `fingerprint`: the 64-bit text-derived identifier shown in the SVG.
- `theme`: the resolved palette, including when `auto` was requested.
- `canvas`: output width and height.
- `graph.connected`: an independently calculated reachability check.
- `graph.backbone_edges` and `graph.local_edges`: edge-layer counts.
- `graph.average_degree` and `graph.max_degree`: graph branching measures.
- `graph.density`: actual edges divided by all possible undirected edges.
- `graph.average_edge_length` and `graph.longest_edge`: pixel-space geometry.

The manifest intentionally omits the original phrase. The SVG still includes
the phrase because it is part of the requested image.

## Validation boundaries

The fingerprint is a compact creative identifier, not a digital signature or
authentication mechanism. Because it displays only 64 bits of SHA-256, it
should not be used to prove authorship or protect security-sensitive data.
