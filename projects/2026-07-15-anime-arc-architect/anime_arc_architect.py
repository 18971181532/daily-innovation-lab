"""Design a deterministic, stateful season outline for an original anime concept."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


class ValidationError(ValueError):
    """Raised when a story specification is internally inconsistent."""


@dataclass(frozen=True)
class Character:
    name: str
    role: str
    goal: str
    fear: str
    trait: str
    faction: str


@dataclass(frozen=True)
class Relation:
    source: str
    target: str
    kind: str
    intensity: int

    @property
    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.source, self.target)))


@dataclass(frozen=True)
class StorySpec:
    title: str
    premise: str
    themes: tuple[str, ...]
    season_length: int
    characters: tuple[Character, ...]
    relations: tuple[Relation, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "StorySpec":
        required = {"title", "premise", "themes", "season_length", "characters", "relations"}
        missing = sorted(required - raw.keys())
        if missing:
            raise ValidationError(f"missing fields: {', '.join(missing)}")

        characters = tuple(Character(**item) for item in raw["characters"])
        relations = tuple(Relation(**item) for item in raw["relations"])
        spec = cls(
            title=str(raw["title"]).strip(),
            premise=str(raw["premise"]).strip(),
            themes=tuple(str(theme).strip() for theme in raw["themes"]),
            season_length=int(raw["season_length"]),
            characters=characters,
            relations=relations,
        )
        spec.validate()
        return spec

    def validate(self) -> None:
        if not self.title or not self.premise:
            raise ValidationError("title and premise must not be empty")
        if not 6 <= self.season_length <= 26:
            raise ValidationError("season_length must be between 6 and 26")
        if not self.themes or any(not theme for theme in self.themes):
            raise ValidationError("at least one non-empty theme is required")
        if len(self.characters) < 3:
            raise ValidationError("at least three characters are required")

        names = [character.name for character in self.characters]
        if any(not name.strip() for name in names):
            raise ValidationError("character names must not be empty")
        if len(names) != len(set(names)):
            raise ValidationError("character names must be unique")
        if not any(character.role.lower() == "protagonist" for character in self.characters):
            raise ValidationError("at least one protagonist is required")

        known = set(names)
        relation_keys: set[tuple[str, str]] = set()
        for relation in self.relations:
            if relation.source not in known or relation.target not in known:
                raise ValidationError(f"unknown character in relation: {relation.source} -> {relation.target}")
            if relation.source == relation.target:
                raise ValidationError("self-relations are not allowed")
            if not -5 <= relation.intensity <= 5:
                raise ValidationError("relation intensity must be between -5 and 5")
            if not relation.kind.strip():
                raise ValidationError("relation kind must not be empty")
            if relation.key in relation_keys:
                raise ValidationError(f"duplicate relation between {relation.source} and {relation.target}")
            relation_keys.add(relation.key)

    def canonical_seed(self) -> int:
        payload = json.dumps(
            {
                "title": self.title,
                "premise": self.premise,
                "themes": self.themes,
                "season_length": self.season_length,
                "characters": [asdict(character) for character in self.characters],
                "relations": [asdict(relation) for relation in self.relations],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


@dataclass(frozen=True)
class StoryBeat:
    label: str
    description: str


@dataclass
class PlotThread:
    thread_id: str
    description: str
    introduced_in: int
    resolved_in: int | None = None


@dataclass(frozen=True)
class EpisodePlan:
    number: int
    title: str
    act: str
    theme: str
    focus: str
    secondary: str
    tension: float
    beats: tuple[StoryBeat, ...]
    introduced_threads: tuple[str, ...]
    resolved_threads: tuple[str, ...]
    relationship_changes: tuple[str, ...]


@dataclass(frozen=True)
class SeasonPlan:
    title: str
    premise: str
    seed: int
    characters: tuple[Character, ...]
    episodes: tuple[EpisodePlan, ...]
    final_relationships: tuple[dict[str, Any], ...]
    threads: tuple[PlotThread, ...]

    @property
    def unresolved_threads(self) -> tuple[PlotThread, ...]:
        return tuple(thread for thread in self.threads if thread.resolved_in is None)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ROLE_WEIGHTS = {
    "protagonist": 2.8,
    "deuteragonist": 1.8,
    "rival": 1.55,
    "mentor": 1.2,
    "antagonist": 1.45,
    "support": 1.0,
}

ACT_TITLE_PATTERNS = {
    "Setup": (
        "A Signal Called {theme}",
        "The Day {focus} Looked Up",
        "Paper Wings over {keyword}",
        "First Contact with {keyword}",
    ),
    "Escalation": (
        "Fault Lines of {theme}",
        "{focus} and the Unpaid Price",
        "The {keyword} Paradox",
        "When Our Promise Fractured",
    ),
    "Climax": (
        "The Last Shape of {theme}",
        "{focus} Chooses the Dawn",
        "Beyond the {keyword} Horizon",
        "What Remains after the Sky",
    ),
}

HOOK_PATTERNS = {
    "Setup": (
        "A routine mission exposes evidence that the season's central mystery is already moving.",
        "A public celebration is interrupted by a private impossibility only the focus character recognizes.",
        "A small failure reveals a rule of the world that someone powerful has been hiding.",
    ),
    "Escalation": (
        "The apparent solution from the previous episode produces a more personal cost.",
        "Two factions pursue the same objective for incompatible reasons.",
        "An old clue changes meaning when viewed through a damaged relationship.",
    ),
    "Climax": (
        "The remaining safe option disappears before the team can agree on a plan.",
        "The antagonist makes a truthful offer whose price would destroy the group's identity.",
        "A recovered memory forces the cast to reinterpret the promise that united them.",
    ),
}

TURN_PATTERNS = {
    "Setup": (
        "The team accepts a mission whose true client remains unknown.",
        "A trusted object responds to the wrong person.",
        "The enemy deliberately leaves behind a clue.",
    ),
    "Escalation": (
        "A victory confirms that the group's original strategy can never solve the real problem.",
        "The secondary character admits a motive that changes the balance of trust.",
        "A rescued witness names someone inside the team.",
    ),
    "Climax": (
        "The focus character gives up the reward they wanted in order to preserve what they learned to value.",
        "A relationship once treated as a weakness becomes the mechanism of victory.",
        "The final choice resolves the external threat but leaves a meaningful new responsibility.",
    ),
}


class ArcArchitect:
    """Generate a season plan while tracking focus, relations, tension, and plot threads."""

    def __init__(self, spec: StorySpec, seed: int | None = None) -> None:
        self.spec = spec
        self.seed = spec.canonical_seed() if seed is None else int(seed)
        self._characters = {character.name: character for character in spec.characters}
        self._relations = {relation.key: relation for relation in spec.relations}

    def generate(self) -> SeasonPlan:
        rng = random.Random(self.seed)
        focus_counts = {name: 0 for name in self._characters}
        recent_focus: list[str] = []
        relation_values = {relation.key: relation.intensity for relation in self.spec.relations}
        threads: list[PlotThread] = []
        episodes: list[EpisodePlan] = []

        for number in range(1, self.spec.season_length + 1):
            act = self._act_for(number)
            theme = self.spec.themes[(number - 1) % len(self.spec.themes)]
            tension = self._tension_for(number, rng)
            focus = self._choose_focus(number, focus_counts, recent_focus, rng)
            secondary = self._choose_secondary(focus, relation_values, rng)
            focus_counts[focus] += 1
            recent_focus = (recent_focus + [focus])[-2:]

            introduced = self._introduce_thread(number, focus, theme, threads, rng)
            resolved = self._resolve_threads(number, threads, tension, rng)
            relationship_changes = self._evolve_relationship(
                focus, secondary, act, tension, relation_values, rng
            )
            beats = self._build_beats(
                act=act,
                focus=focus,
                secondary=secondary,
                theme=theme,
                tension=tension,
                open_threads=[thread for thread in threads if thread.resolved_in is None],
                introduced=introduced,
                resolved=resolved,
                rng=rng,
            )
            episodes.append(
                EpisodePlan(
                    number=number,
                    title=self._episode_title(act, focus, theme, rng),
                    act=act,
                    theme=theme,
                    focus=focus,
                    secondary=secondary,
                    tension=tension,
                    beats=tuple(beats),
                    introduced_threads=tuple(thread.description for thread in introduced),
                    resolved_threads=tuple(thread.description for thread in resolved),
                    relationship_changes=tuple(relationship_changes),
                )
            )

        final_relationships = []
        for key, relation in sorted(self._relations.items()):
            final_relationships.append(
                {
                    "characters": list(key),
                    "kind": relation.kind,
                    "initial_intensity": relation.intensity,
                    "final_intensity": relation_values[key],
                }
            )

        return SeasonPlan(
            title=self.spec.title,
            premise=self.spec.premise,
            seed=self.seed,
            characters=self.spec.characters,
            episodes=tuple(episodes),
            final_relationships=tuple(final_relationships),
            threads=tuple(threads),
        )

    def _act_for(self, number: int) -> str:
        progress = number / self.spec.season_length
        if progress <= 0.25:
            return "Setup"
        if progress <= 0.75:
            return "Escalation"
        return "Climax"

    def _tension_for(self, number: int, rng: random.Random) -> float:
        progress = (number - 1) / max(1, self.spec.season_length - 1)
        if progress < 0.25:
            tension = 2.8 + 2.5 * self._smoothstep(progress / 0.25)
        elif progress < 0.68:
            tension = 5.0 + 2.7 * self._smoothstep((progress - 0.25) / 0.43)
        elif progress < 0.88:
            tension = 7.4 + 2.2 * self._smoothstep((progress - 0.68) / 0.20)
        else:
            tension = 9.6 - 2.1 * self._smoothstep((progress - 0.88) / 0.12)
        if number not in {1, self.spec.season_length}:
            tension += rng.uniform(-0.28, 0.28)
        return round(max(1.0, min(10.0, tension)), 1)

    @staticmethod
    def _smoothstep(value: float) -> float:
        value = max(0.0, min(1.0, value))
        return value * value * (3.0 - 2.0 * value)

    def _choose_focus(
        self,
        number: int,
        counts: dict[str, int],
        recent: list[str],
        rng: random.Random,
    ) -> str:
        protagonists = [character.name for character in self.spec.characters if character.role.lower() == "protagonist"]
        if number in {1, self.spec.season_length}:
            return min(protagonists, key=lambda name: counts[name])

        weighted: list[tuple[str, float]] = []
        for character in self.spec.characters:
            base = ROLE_WEIGHTS.get(character.role.lower(), 1.0)
            balance = 1.0 / (1.0 + counts[character.name] * 0.72)
            recent_penalty = 0.24 if character.name in recent else 1.0
            weighted.append((character.name, base * balance * recent_penalty))
        return self._weighted_choice(weighted, rng)

    def _choose_secondary(
        self,
        focus: str,
        relation_values: dict[tuple[str, str], int],
        rng: random.Random,
    ) -> str:
        weighted: list[tuple[str, float]] = []
        for candidate in self._characters:
            if candidate == focus:
                continue
            key = tuple(sorted((focus, candidate)))
            if key in self._relations:
                relation = self._relations[key]
                weight = 2.0 + abs(relation_values[key]) * 0.45
                if relation.kind.lower() in {"rivalry", "secret", "debt"}:
                    weight += 0.8
            else:
                weight = 0.45
            weighted.append((candidate, weight))
        return self._weighted_choice(weighted, rng)

    @staticmethod
    def _weighted_choice(weighted: Iterable[tuple[str, float]], rng: random.Random) -> str:
        items = sorted(weighted, key=lambda item: item[0])
        total = sum(max(0.0, weight) for _, weight in items)
        if total <= 0:
            raise RuntimeError("weighted choice has no positive candidates")
        marker = rng.random() * total
        upto = 0.0
        for value, weight in items:
            upto += max(0.0, weight)
            if marker <= upto:
                return value
        return items[-1][0]

    def _introduce_thread(
        self,
        number: int,
        focus: str,
        theme: str,
        threads: list[PlotThread],
        rng: random.Random,
    ) -> list[PlotThread]:
        last_introduction = max(2, math.floor(self.spec.season_length * 0.58))
        if number > last_introduction:
            return []
        character = self._characters[focus]
        patterns = (
            "why {faction} erased a record connected to {theme}",
            "the real cost of {focus}'s goal: {goal}",
            "who benefits when {focus}'s fear becomes public",
            "the origin of the symbol found near {faction}",
        )
        description = rng.choice(patterns).format(
            faction=character.faction,
            theme=theme,
            focus=focus,
            goal=character.goal,
        )
        thread = PlotThread(
            thread_id=f"T{len(threads) + 1:02d}",
            description=description,
            introduced_in=number,
        )
        threads.append(thread)
        return [thread]

    def _resolve_threads(
        self,
        number: int,
        threads: list[PlotThread],
        tension: float,
        rng: random.Random,
    ) -> list[PlotThread]:
        open_threads = [thread for thread in threads if thread.resolved_in is None and thread.introduced_in < number]
        if not open_threads:
            return []
        if number == self.spec.season_length:
            for thread in open_threads:
                thread.resolved_in = number
            return open_threads

        earliest_resolution = math.ceil(self.spec.season_length * 0.46)
        should_resolve = number >= earliest_resolution and (number % 2 == 0 or tension >= 8.3)
        if not should_resolve:
            return []
        candidates = sorted(open_threads, key=lambda thread: (thread.introduced_in, thread.thread_id))
        chosen = candidates[0] if rng.random() < 0.75 else rng.choice(candidates)
        chosen.resolved_in = number
        return [chosen]

    def _evolve_relationship(
        self,
        focus: str,
        secondary: str,
        act: str,
        tension: float,
        relation_values: dict[tuple[str, str], int],
        rng: random.Random,
    ) -> list[str]:
        key = tuple(sorted((focus, secondary)))
        if key not in self._relations:
            return [f"{focus} and {secondary} form a fragile working connection."]

        relation = self._relations[key]
        old_value = relation_values[key]
        kind = relation.kind.lower()
        if act == "Setup":
            delta = -1 if kind in {"rivalry", "secret", "debt"} else 1
        elif act == "Escalation":
            delta = rng.choice((-2, -1, 1)) if tension >= 6.5 else rng.choice((-1, 1))
        else:
            delta = 2 if old_value < 0 else 1

        new_value = max(-5, min(5, old_value + delta))
        relation_values[key] = new_value
        direction = "deepens" if new_value > old_value else "fractures" if new_value < old_value else "holds"
        return [
            f"Their {relation.kind} {direction}: {focus} ↔ {secondary} shifts from {old_value:+d} to {new_value:+d}."
        ]

    def _build_beats(
        self,
        *,
        act: str,
        focus: str,
        secondary: str,
        theme: str,
        tension: float,
        open_threads: list[PlotThread],
        introduced: list[PlotThread],
        resolved: list[PlotThread],
        rng: random.Random,
    ) -> list[StoryBeat]:
        focus_character = self._characters[focus]
        secondary_character = self._characters[secondary]
        hook = rng.choice(HOOK_PATTERNS[act])
        if open_threads:
            hook += f" The oldest active question concerns {open_threads[0].description}."

        choice = (
            f"{focus} pursues “{focus_character.goal}” but must act through their fear of "
            f"{focus_character.fear}; the decision highlights their {focus_character.trait} nature."
        )
        pressure = (
            f"{secondary}, representing {secondary_character.faction}, challenges the method rather than the goal. "
            f"At tension {tension:.1f}/10, compromise carries a visible cost."
        )
        if resolved:
            turn = f"The cast resolves {resolved[0].description}, but the answer transfers responsibility to {focus}."
        elif introduced:
            turn = f"A new question takes control of the ending: {introduced[0].description}."
        else:
            turn = rng.choice(TURN_PATTERNS[act])

        return [
            StoryBeat("Cold open", hook),
            StoryBeat("Character choice", choice),
            StoryBeat("Relational pressure", pressure),
            StoryBeat("Ending turn", turn),
        ]

    def _episode_title(self, act: str, focus: str, theme: str, rng: random.Random) -> str:
        keyword = self._keyword(theme)
        return rng.choice(ACT_TITLE_PATTERNS[act]).format(theme=theme.title(), focus=focus, keyword=keyword.title())

    @staticmethod
    def _keyword(text: str) -> str:
        words = re.findall(r"[A-Za-z0-9]+", text)
        ignored = {"a", "an", "and", "of", "the", "to", "versus", "vs"}
        useful = [word for word in words if word.lower() not in ignored]
        return useful[-1] if useful else "Unknown"


def load_spec(path: Path) -> StorySpec:
    return StorySpec.from_dict(json.loads(path.read_text(encoding="utf-8")))


def render_markdown(plan: SeasonPlan) -> str:
    lines = [
        f"# {plan.title} — Season Architecture",
        "",
        plan.premise,
        "",
        f"Deterministic seed: `{plan.seed}`",
        "",
        "## Cast",
        "",
        "| Character | Role | Faction | Goal | Fear |",
        "|---|---|---|---|---|",
    ]
    for character in plan.characters:
        lines.append(
            f"| {character.name} | {character.role} | {character.faction} | {character.goal} | {character.fear} |"
        )

    lines.extend(
        [
            "",
            "## Season at a glance",
            "",
            "| Ep. | Act | Title | Focus | Secondary | Theme | Tension |",
            "|---:|---|---|---|---|---|---:|",
        ]
    )
    for episode in plan.episodes:
        lines.append(
            f"| {episode.number} | {episode.act} | {episode.title} | {episode.focus} | "
            f"{episode.secondary} | {episode.theme} | {episode.tension:.1f} |"
        )

    lines.extend(["", "## Episode cards", ""])
    for episode in plan.episodes:
        lines.extend(
            [
                f"### Episode {episode.number}: {episode.title}",
                "",
                f"**{episode.act} · Focus: {episode.focus} · Theme: {episode.theme} · Tension: {episode.tension:.1f}/10**",
                "",
            ]
        )
        for beat in episode.beats:
            lines.append(f"- **{beat.label}:** {beat.description}")
        for change in episode.relationship_changes:
            lines.append(f"- **Relationship:** {change}")
        for thread in episode.introduced_threads:
            lines.append(f"- **Thread opened:** {thread}")
        for thread in episode.resolved_threads:
            lines.append(f"- **Thread resolved:** {thread}")
        lines.append("")

    lines.extend(
        [
            "## Relationship ledger",
            "",
            "| Pair | Dynamic | Start | End |",
            "|---|---|---:|---:|",
        ]
    )
    for relation in plan.final_relationships:
        pair = " ↔ ".join(relation["characters"])
        lines.append(
            f"| {pair} | {relation['kind']} | {relation['initial_intensity']:+d} | {relation['final_intensity']:+d} |"
        )
    lines.extend(
        [
            "",
            "## Continuity check",
            "",
            f"Open threads after the finale: **{len(plan.unresolved_threads)}**",
            "",
        ]
    )
    return "\n".join(lines)


def render_tension_svg(plan: SeasonPlan, width: int = 1100, height: int = 440) -> str:
    padding_x, padding_y = 72, 62
    plot_width, plot_height = width - padding_x * 2, height - padding_y * 2
    count = len(plan.episodes)
    points: list[tuple[float, float]] = []
    for index, episode in enumerate(plan.episodes):
        x = padding_x + index * plot_width / max(1, count - 1)
        y = padding_y + (10.0 - episode.tension) / 9.0 * plot_height
        points.append((x, y))

    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    safe_title = html.escape(plan.title)
    elements = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f"<title>Tension curve for {safe_title}</title>",
        '<rect width="100%" height="100%" fill="#101522"/>',
        f'<text x="{padding_x}" y="32" fill="#f6f2ff" font-family="system-ui" font-size="20">{safe_title} — season tension</text>',
    ]
    for level in range(1, 11):
        y = padding_y + (10 - level) / 9 * plot_height
        elements.append(f'<line x1="{padding_x}" y1="{y:.1f}" x2="{width-padding_x}" y2="{y:.1f}" stroke="#273149"/>')
        elements.append(f'<text x="48" y="{y+4:.1f}" fill="#8792aa" font-family="monospace" font-size="12">{level}</text>')
    elements.append(f'<polyline points="{polyline}" fill="none" stroke="#ff7ac6" stroke-width="4" stroke-linejoin="round"/>')
    for episode, (x, y) in zip(plan.episodes, points):
        elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#74e6ff" stroke="#101522" stroke-width="2"/>')
        elements.append(f'<text x="{x:.1f}" y="{height-24}" text-anchor="middle" fill="#cbd5e8" font-family="monospace" font-size="12">E{episode.number}</text>')
    elements.append("</svg>")
    return "\n".join(elements)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path, help="JSON season specification")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("examples"))
    parser.add_argument("--seed", type=int, help="override the deterministic seed")
    args = parser.parse_args()

    spec = load_spec(args.spec)
    plan = ArcArchitect(spec, seed=args.seed).generate()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "season_plan.json").write_text(
        json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.output_dir / "season_plan.md").write_text(render_markdown(plan), encoding="utf-8")
    (args.output_dir / "tension_curve.svg").write_text(render_tension_svg(plan), encoding="utf-8")
    print(f"Created a {len(plan.episodes)}-episode plan in {args.output_dir}")


if __name__ == "__main__":
    main()
