import unittest

from constellation import render_constellation


class RenderConstellationTests(unittest.TestCase):
    def test_same_text_is_deterministic(self) -> None:
        first = render_constellation("Curiosity builds constellations")
        second = render_constellation("Curiosity builds constellations")
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

    def test_rejects_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            render_constellation("   ")
        with self.assertRaises(ValueError):
            render_constellation("too few", count=4)


if __name__ == "__main__":
    unittest.main()
