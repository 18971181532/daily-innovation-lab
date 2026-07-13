"""Turn a short piece of text into a deterministic constellation SVG."""

from __future__ import annotations

import argparse
import hashlib
import html
import math
import random
from pathlib import Path


def _seed(text: str) -> int:
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


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


def _edges(points: list[tuple[float, float, float]]) -> list[tuple[int, int, float]]:
    edges: set[tuple[int, int]] = set()
    for index, (x1, y1, _) in enumerate(points):
        distances = sorted(
            (
                (math.hypot(x1 - x2, y1 - y2), other)
                for other, (x2, y2, _) in enumerate(points)
                if other != index
            ),
            key=lambda item: item[0],
        )
        for _, other in distances[:2]:
            edges.add(tuple(sorted((index, other))))

    return [
        (left, right, math.hypot(points[left][0] - points[right][0], points[left][1] - points[right][1]))
        for left, right in sorted(edges)
    ]


def render_constellation(text: str, *, count: int = 28, width: int = 1200, height: int = 630) -> str:
    """Return an SVG constellation derived from *text*.

    The result is deterministic: identical arguments always produce identical SVG.
    """

    if not text.strip():
        raise ValueError("text must not be empty")
    if not 5 <= count <= 200:
        raise ValueError("count must be between 5 and 200")
    if width < 320 or height < 240:
        raise ValueError("canvas must be at least 320 x 240")

    seed = _seed(text)
    points = _points(text, count, width, height)
    hue = seed % 360
    accent = (hue + 52) % 360
    safe_text = html.escape(text)
    max_distance = math.hypot(width, height) * 0.24

    lines = []
    for left, right, distance in _edges(points):
        if distance > max_distance:
            continue
        x1, y1, _ = points[left]
        x2, y2, _ = points[right]
        opacity = max(0.12, 0.62 * (1 - distance / max_distance))
        lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="hsl({accent} 86% 76%)" stroke-opacity="{opacity:.3f}" />'
        )

    stars = [
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="white" '
        f'fill-opacity="{0.58 + radius / 13:.3f}" />'
        for x, y, radius in points
    ]

    return "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            f"  <title>Constellation for {safe_text}</title>",
            "  <defs>",
            f'    <radialGradient id="sky"><stop stop-color="hsl({hue} 54% 23%)"/><stop offset="1" stop-color="hsl({hue} 72% 6%)"/></radialGradient>',
            "  </defs>",
            f'  <rect width="{width}" height="{height}" fill="url(#sky)"/>',
            f'  <g stroke-width="1.35">{"".join(lines)}</g>',
            f'  <g>{"".join(stars)}</g>',
            f'  <text x="48" y="{height - 48}" fill="white" fill-opacity="0.82" font-family="system-ui, sans-serif" font-size="24">{safe_text}</text>',
            f'  <text x="{width - 48}" y="{height - 48}" text-anchor="end" fill="white" fill-opacity="0.42" font-family="monospace" font-size="14">seed {seed:016x}</text>',
            "</svg>",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="text used to seed the constellation")
    parser.add_argument("-o", "--output", type=Path, default=Path("constellation.svg"))
    parser.add_argument("--points", type=int, default=28, help="number of stars (5-200)")
    args = parser.parse_args()

    args.output.write_text(render_constellation(args.text, count=args.points), encoding="utf-8")
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
