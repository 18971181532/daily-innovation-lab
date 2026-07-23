import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from constellation import THEMES, build_manifest, render_constellation


class RenderConstellationTests(unittest.TestCase):
    def test_same_arguments_are_deterministic(self) -> None:
        first = render_constellation("Curiosity builds constellations", theme="aurora")
        second = render_constellation("Curiosity builds constellations", theme="aurora")
        self.assertEqual(first, second)

    def test_different_text_changes_the_result(self) -> None:
        self.assertNotEqual(render_constellation("alpha"), render_constellation("beta"))

    def test_text_is_xml_escaped(self) -> None:
        svg = render_constellation("<ideas & stars>")
        self.assertIn("&lt;ideas &amp; stars&gt;", svg)
        self.assertNotIn("<ideas & stars>", svg)

    def test_requested_star_count_is_rendered(self) -> None:
        svg = render_constellation("seven", count=7)
        self.assertEqual(svg.count("<circle "), 7)
        self.assertEqual(build_manifest("seven", count=7)["graph"]["stars"], 7)

    def test_svg_is_valid_xml_with_accessible_description(self) -> None:
        svg = render_constellation("Accessible stars")
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib["role"], "img")
        self.assertEqual(root.attrib["aria-labelledby"], "title description")
        self.assertEqual(root.attrib["preserveAspectRatio"], "xMidYMid meet")
        self.assertIn("max-width:100%", root.attrib["style"])
        self.assertIn("height:auto", root.attrib["style"])
        self.assertTrue(root.find("{http://www.w3.org/2000/svg}desc").text)

    def test_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            render_constellation("   ")
        with self.assertRaises(ValueError):
            render_constellation("too few", count=4)
        with self.assertRaises(ValueError):
            render_constellation("tiny canvas", width=319)
        with self.assertRaises(ValueError):
            render_constellation("unknown palette", theme="ocean")


class ConstellationGraphTests(unittest.TestCase):
    def test_minimum_spanning_backbone_connects_every_star(self) -> None:
        for count in (5, 28, 80):
            with self.subTest(count=count):
                graph = build_manifest("Every point belongs", count=count)["graph"]
                self.assertTrue(graph["connected"])
                self.assertEqual(graph["backbone_edges"], count - 1)

    def test_graph_statistics_are_internally_consistent(self) -> None:
        graph = build_manifest("Metrics should tell one story", count=32)["graph"]
        self.assertEqual(graph["edges"], graph["backbone_edges"] + graph["local_edges"])
        self.assertGreaterEqual(graph["average_degree"], 2 * graph["backbone_edges"] / graph["stars"])
        self.assertGreater(graph["longest_edge"], graph["average_edge_length"])
        self.assertGreater(graph["density"], 0)
        self.assertLessEqual(graph["density"], 1)

    def test_auto_theme_is_deterministic_and_known(self) -> None:
        first = build_manifest("Let the seed choose")
        second = build_manifest("Let the seed choose")
        self.assertEqual(first["theme"], second["theme"])
        self.assertIn(first["theme"], THEMES)

    def test_explicit_themes_change_palette_not_fingerprint(self) -> None:
        aurora = build_manifest("One geometry, many moods", theme="aurora")
        ember = build_manifest("One geometry, many moods", theme="ember")
        self.assertEqual(aurora["fingerprint"], ember["fingerprint"])
        self.assertNotEqual(aurora["theme"], ember["theme"])
        self.assertNotEqual(
            render_constellation("One geometry, many moods", theme="aurora"),
            render_constellation("One geometry, many moods", theme="ember"),
        )

    def test_manifest_does_not_repeat_private_input_text(self) -> None:
        secret_phrase = "private draft title"
        encoded = json.dumps(build_manifest(secret_phrase))
        self.assertNotIn(secret_phrase, encoded)
        self.assertIn("fingerprint", encoded)

    def test_manifest_round_trips_as_json(self) -> None:
        manifest = build_manifest("Portable metadata", count=17, width=900, height=500)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            restored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(restored, manifest)


if __name__ == "__main__":
    unittest.main()
