import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from anime_arc_architect import (
    ArcArchitect,
    StorySpec,
    ValidationError,
    load_spec,
    render_markdown,
    render_tension_svg,
)


ROOT = Path(__file__).resolve().parents[1]


class ArcArchitectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_spec(ROOT / "sample_season.json")

    def test_sample_generates_complete_season(self) -> None:
        plan = ArcArchitect(self.spec).generate()
        self.assertEqual(len(plan.episodes), 12)
        self.assertEqual([episode.number for episode in plan.episodes], list(range(1, 13)))
        self.assertEqual(plan.unresolved_threads, ())

    def test_generation_is_deterministic(self) -> None:
        first = ArcArchitect(self.spec).generate().to_dict()
        second = ArcArchitect(self.spec).generate().to_dict()
        self.assertEqual(first, second)
        self.assertNotEqual(first, ArcArchitect(self.spec, seed=99).generate().to_dict())

    def test_tension_and_focus_are_balanced(self) -> None:
        plan = ArcArchitect(self.spec).generate()
        self.assertTrue(all(1.0 <= episode.tension <= 10.0 for episode in plan.episodes))
        focus_names = {episode.focus for episode in plan.episodes}
        self.assertGreaterEqual(len(focus_names), len(self.spec.characters) - 1)
        self.assertEqual(plan.episodes[0].focus, "Mina Kisaragi")
        self.assertEqual(plan.episodes[-1].focus, "Mina Kisaragi")

    def test_every_episode_has_structural_beats(self) -> None:
        plan = ArcArchitect(self.spec).generate()
        for episode in plan.episodes:
            self.assertEqual([beat.label for beat in episode.beats], [
                "Cold open",
                "Character choice",
                "Relational pressure",
                "Ending turn",
            ])
            self.assertTrue(episode.relationship_changes)

    def test_markdown_contains_cast_and_episode_cards(self) -> None:
        markdown = render_markdown(ArcArchitect(self.spec).generate())
        self.assertIn("# Neon Paper Cranes — Season Architecture", markdown)
        self.assertIn("### Episode 12:", markdown)
        self.assertIn("Mina Kisaragi", markdown)
        self.assertIn("Open threads after the finale: **0**", markdown)

    def test_svg_is_valid_xml_and_has_episode_points(self) -> None:
        svg = render_tension_svg(ArcArchitect(self.spec).generate())
        root = ET.fromstring(svg)
        circles = root.findall("{http://www.w3.org/2000/svg}circle")
        self.assertEqual(len(circles), self.spec.season_length)

    def test_rejects_duplicate_character_names(self) -> None:
        raw = json.loads((ROOT / "sample_season.json").read_text(encoding="utf-8"))
        raw["characters"][1]["name"] = raw["characters"][0]["name"]
        with self.assertRaisesRegex(ValidationError, "unique"):
            StorySpec.from_dict(raw)

    def test_rejects_unknown_relation_character(self) -> None:
        raw = json.loads((ROOT / "sample_season.json").read_text(encoding="utf-8"))
        raw["relations"][0]["target"] = "Nobody"
        with self.assertRaisesRegex(ValidationError, "unknown character"):
            StorySpec.from_dict(raw)

    def test_cli_input_loader_uses_utf8(self) -> None:
        raw = json.loads((ROOT / "sample_season.json").read_text(encoding="utf-8"))
        raw["title"] = "星の記憶"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spec.json"
            path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
            self.assertEqual(load_spec(path).title, "星の記憶")


if __name__ == "__main__":
    unittest.main()
