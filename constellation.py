"""Turn text into a deterministic, connected constellation and analysis manifest."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

VERSION = "0.2.0"


@dataclass(frozen=True)
class Theme:
    """A deterministic palette recipe anchored to the text-derived hue."""

    name: str
    hue_shift: int
    accent_shift: int
    sky_saturation: int
    sky_lightness: int
    edge_saturation: int
    edge_lightness: int
    star_color: str
    glow_color: str


@dataclass(frozen=True)
class Edge:
    """A graph edge between two stars."""

    left: int
    right: int
    distance: float
    kind: str


THEMES: dict[str, Theme] = {
    "aurora": Theme("aurora", 0, 52, 62, 22, 86, 76, "#f8fbff", "#8ef4ff"),
    "ember": Theme("ember", 18, 28, 68, 18, 92, 69, "#fff5e8", "#ffb36b"),
    "nebula": Theme("nebula", 224, 76, 58, 20, 82, 79, "#f7f1ff", "#c7a4ff"),
}


def _seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def _validate(text: str, count: int, width: int, height: int, theme: str) -> None:
    if not text.strip():
        raise ValueError("text must not be empty")
    if not 5 <= count <= 200:
        raise ValueError("count must be between 5 and 200")
    if width < 320 or height < 240:
        raise ValueError("canvas must be at least 320 x 240")
    if theme != "auto" and theme not in THEMES:
        choices = ", ".join(("auto", *THEMES))
        raise ValueError(f"theme must be one of: {choices}")


def _resolve_theme(theme: str, seed: int) -> Theme:
    if theme == "auto":
        names = tuple(sorted(THEMES))
        theme = names[seed % len(names)]
    return THEMES[theme]


def _points(text: str, count: int, width: int, height: int) -> list[tuple[float, float, float]]:
    rng = random.Random(_seed(text))
    padding = min(width, height) * 0.09
    return [
        (
            rng.uniform(padding, width - padding),
            rng.uniform(padding, height - padding),
            rng.uniform(1.8, 5.2),
        )
        for _ in range(count)
    ]


def _distance(
    points: list[tuple[float, float, float]],
    left: int,
    right: int,
) -> float:
    return math.hypot(points[left][0] - points[right][0], points[left][1] - points[right][1])


def _nearest_indices(
    points: list[tuple[float, float, float]],
    index: int,
    count: int,
) -> Iterable[int]:
    distances = (
        (_distance(points, index, other), other)
        for other in range(len(points))
        if other != index
    )
    return (other for _, other in sorted(distances, key=lambda item: (item[0], item[1]))[:count])


def _connected_edges(points: list[tuple[float, float, float]]) -> list[Edge]:
    """Build a minimum-spanning backbone plus local nearest-neighbour details."""

    connected = {0}
    backbone: set[tuple[int, int]] = set()

    while len(connected) < len(points):
        candidates = (
            (_distance(points, left, right), left, right)
            for left in connected
            for right in range(len(points))
            if right not in connected
        )
        _, left, right = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        pair = tuple(sorted((left, right)))
        backbone.add(pair)
        connected.add(right)

    local: set[tuple[int, int]] = set()
    for index in range(len(points)):
        for other in _nearest_indices(points, index, 2):
            pair = tuple(sorted((index, other)))
            if pair not in backbone:
                local.add(pair)

    edges = [
        Edge(left, right, _distance(points, left, right), "backbone")
        for left, right in backbone
    ]
    edges.extend(
        Edge(left, right, _distance(points, left, right), "local")
        for left, right in local
    )
    return sorted(edges, key=lambda edge: (edge.left, edge.right, edge.kind))


def _is_connected(count: int, edges: list[Edge]) -> bool:
    neighbours: list[set[int]] = [set() for _ in range(count)]
    for edge in edges:
        neighbours[edge.left].add(edge.right)
        neighbours[edge.right].add(edge.left)

    visited = {0}
    frontier = [0]
    while frontier:
        node = frontier.pop()
        for neighbour in neighbours[node] - visited:
            visited.add(neighbour)
            frontier.append(neighbour)
    return len(visited) == count


def _prepare(
    text: str,
    count: int,
    width: int,
    height: int,
    theme: str,
) -> tuple[int, Theme, list[tuple[float, float, float]], list[Edge]]:
    _validate(text, count, width, height, theme)
    seed = _seed(text)
    points = _points(text, count, width, height)
    edges = _connected_edges(points)
    return seed, _resolve_theme(theme, seed), points, edges


def _manifest_from(
    seed: int,
    theme: Theme,
    points: list[tuple[float, float, float]],
    edges: list[Edge],
    width: int,
    height: int,
) -> dict[str, object]:
    edge_count = len(edges)
    star_count = len(points)
    total_length = sum(edge.distance for edge in edges)
    degrees = [0] * star_count
    for edge in edges:
        degrees[edge.left] += 1
        degrees[edge.right] += 1

    return {
        "generator": "text-constellation",
        "version": VERSION,
        "fingerprint": f"{seed:016x}",
        "theme": theme.name,
        "canvas": {"width": width, "height": height},
        "graph": {
            "connected": _is_connected(star_count, edges),
            "stars": star_count,
            "edges": edge_count,
            "backbone_edges": sum(edge.kind == "backbone" for edge in edges),
            "local_edges": sum(edge.kind == "local" for edge in edges),
            "average_degree": round(sum(degrees) / star_count, 3),
            "max_degree": max(degrees),
            "density": round(2 * edge_count / (star_count * (star_count - 1)), 5),
            "average_edge_length": round(total_length / edge_count, 3),
            "longest_edge": round(max(edge.distance for edge in edges), 3),
        },
    }


def build_manifest(
    text: str,
    *,
    count: int = 28,
    width: int = 1200,
    height: int = 630,
    theme: str = "auto",
) -> dict[str, object]:
    """Return reproducible graph and palette metadata without exposing the input text."""

    seed, resolved_theme, points, edges = _prepare(text, count, width, height, theme)
    return _manifest_from(seed, resolved_theme, points, edges, width, height)


def render_constellation(
    text: str,
    *,
    count: int = 28,
    width: int = 1200,
    height: int = 630,
    theme: str = "auto",
) -> str:
    """Return an accessible SVG constellation derived from *text*.

    Identical arguments always produce identical SVG. A minimum-spanning
    backbone guarantees that every star belongs to one connected graph.
    """

    seed, resolved_theme, points, edges = _prepare(text, count, width, height, theme)
    manifest = _manifest_from(seed, resolved_theme, points, edges, width, height)
    base_hue = (seed + resolved_theme.hue_shift) % 360
    accent_hue = (base_hue + resolved_theme.accent_shift) % 360
    safe_text = html.escape(text)
    safe_manifest = html.escape(json.dumps(manifest, separators=(",", ":"), sort_keys=True))
    diagonal = math.hypot(width, height)

    edge_groups: dict[str, list[str]] = {"backbone": [], "local": []}
    for edge in edges:
        x1, y1, _ = points[edge.left]
        x2, y2, _ = points[edge.right]
        opacity = max(0.09, 0.72 * (1 - edge.distance / diagonal))
        edge_groups[edge.kind].append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke-opacity="{opacity:.3f}" data-edge="{edge.left}-{edge.right}" />'
        )

    stars = [
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" '
        f'fill="{resolved_theme.star_color}" fill-opacity="{0.58 + radius / 13:.3f}" data-star="{index}" />'
        for index, (x, y, radius) in enumerate(points)
    ]

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description" '
                f'preserveAspectRatio="xMidYMid meet" style="max-width:100%;height:auto;display:block" '
                f'data-theme="{resolved_theme.name}" data-fingerprint="{seed:016x}">'
            ),
            f'  <title id="title">Constellation for {safe_text}</title>',
            (
                '  <desc id="description">'
                f'Deterministic connected constellation with {len(points)} stars and {len(edges)} edges.'
                "</desc>"
            ),
            f"  <metadata>{safe_manifest}</metadata>",
            "  <defs>",
            (
                f'    <radialGradient id="sky"><stop stop-color="hsl({base_hue} '
                f'{resolved_theme.sky_saturation}% {resolved_theme.sky_lightness}%)"/>'
                f'<stop offset="1" stop-color="hsl({base_hue} 72% 5%)"/></radialGradient>'
            ),
            (
                f'    <filter id="glow"><feFlood flood-color="{resolved_theme.glow_color}" '
                'flood-opacity=".65"/><feComposite in2="SourceGraphic" operator="in"/>'
                '<feGaussianBlur stdDeviation="2.4"/><feMerge><feMergeNode/>'
                '<feMergeNode in="SourceGraphic"/></feMerge></filter>'
            ),
            "  </defs>",
            f'  <rect width="{width}" height="{height}" fill="url(#sky)"/>',
            (
                f'  <g class="backbone" stroke="hsl({accent_hue} '
                f'{resolved_theme.edge_saturation}% {resolved_theme.edge_lightness}%)" '
                f'stroke-width="1.4">{"".join(edge_groups["backbone"])}</g>'
            ),
            (
                f'  <g class="local" stroke="hsl({accent_hue} '
                f'{resolved_theme.edge_saturation}% {resolved_theme.edge_lightness}%)" '
                f'stroke-width=".85">{"".join(edge_groups["local"])}</g>'
            ),
            f'  <g filter="url(#glow)">{"".join(stars)}</g>',
            (
                f'  <text x="48" y="{height - 48}" fill="white" fill-opacity="0.84" '
                f'font-family="system-ui, sans-serif" font-size="24">{safe_text}</text>'
            ),
            (
                f'  <text x="{width - 48}" y="{height - 48}" text-anchor="end" fill="white" '
                f'fill-opacity="0.46" font-family="monospace" font-size="14">'
                f'{resolved_theme.name} · {seed:016x}</text>'
            ),
            "</svg>",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="text used to seed the constellation")
    parser.add_argument("-o", "--output", type=Path, default=Path("constellation.svg"))
    parser.add_argument("--points", type=int, default=28, help="number of stars (5-200)")
    parser.add_argument("--width", type=int, default=1200, help="SVG width in pixels")
    parser.add_argument("--height", type=int, default=630, help="SVG height in pixels")
    parser.add_argument("--theme", choices=("auto", *THEMES), default="auto")
    parser.add_argument("--manifest", type=Path, help="optional JSON analysis sidecar")
    args = parser.parse_args()

    svg = render_constellation(
        args.text,
        count=args.points,
        width=args.width,
        height=args.height,
        theme=args.theme,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg + "\n", encoding="utf-8")
    print(f"Created {args.output}")

    if args.manifest:
        manifest = build_manifest(
            args.text,
            count=args.points,
            width=args.width,
            height=args.height,
            theme=args.theme,
        )
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Created {args.manifest}")


if __name__ == "__main__":
    main()
