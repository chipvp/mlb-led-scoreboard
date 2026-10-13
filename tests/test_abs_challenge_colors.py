import json
import unittest
from unittest import mock

from data.config.color import Color
from data.config.layout import Layout
from data.scoreboard.team import Team
from renderers.games import teams as team_renderer
from renderers.games.teams import _MIN_LIT_CONTRAST, _MIN_LIT_LUMINANCE, _contrast, _luminance, abs_challenge_colors

YELLOW = {"r": 255, "g": 235, "b": 59}
DIM_YELLOW = {"r": 100, "g": 90, "b": 22}
GUARDIANS_BANNER = {"r": 227, "g": 227, "b": 239}
GUARDIANS_TEXT = {"r": 11, "g": 34, "b": 63}
GUARDIANS_RED = {"r": 204, "g": 0, "b": 46}
NAVY = {"r": 0, "g": 20, "b": 70}
WHITE = {"r": 255, "g": 255, "b": 255}
BLACK = {"r": 0, "g": 0, "b": 0}


class TestAbsChallengeColors(unittest.TestCase):
    def test_contrast_ratio_extremes(self):
        self.assertAlmostEqual(_contrast(BLACK, WHITE), 21.0, places=1)
        self.assertAlmostEqual(_contrast(WHITE, WHITE), 1.0)

    def test_configured_colors_kept_on_a_dark_banner(self):
        self.assertEqual(abs_challenge_colors(YELLOW, DIM_YELLOW, NAVY, WHITE, BLACK), (YELLOW, DIM_YELLOW))

    def test_yellow_on_a_white_banner_falls_back_to_the_side_bar_color(self):
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_TEXT, GUARDIANS_RED)
        self.assertEqual(available, GUARDIANS_RED)
        self.assertGreaterEqual(_contrast(available, GUARDIANS_BANNER), 3.0)

    def test_a_dark_text_color_is_skipped_for_a_lit_side_bar_color(self):
        # navy contrasts with the banner far better than red does, but it reads as an unlit LED
        self.assertGreater(_contrast(GUARDIANS_TEXT, GUARDIANS_BANNER), _contrast(GUARDIANS_RED, GUARDIANS_BANNER))
        self.assertLess(_luminance(GUARDIANS_TEXT), _MIN_LIT_LUMINANCE)
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_TEXT, GUARDIANS_RED)
        self.assertNotEqual(available, GUARDIANS_TEXT)

    def test_text_color_is_used_when_the_side_bar_color_does_not_read(self):
        faint_accent = {"r": 240, "g": 240, "b": 245}
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_RED, faint_accent)
        self.assertEqual(available, GUARDIANS_RED)

    def test_spent_challenge_is_dimmer_than_available_but_not_the_banner_color(self):
        available, spent = abs_challenge_colors(YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_TEXT, GUARDIANS_RED)
        self.assertNotEqual(spent, available)
        self.assertNotEqual(spent, GUARDIANS_BANNER)
        self.assertLess(_contrast(spent, GUARDIANS_BANNER), _contrast(available, GUARDIANS_BANNER))

    def test_keeps_configured_colors_when_no_team_color_is_better(self):
        # yellow on a light banner with equally poor team colors: nothing to gain by swapping
        banner = {"r": 250, "g": 250, "b": 250}
        text, accent = {"r": 245, "g": 245, "b": 245}, {"r": 248, "g": 248, "b": 248}
        self.assertEqual(abs_challenge_colors(YELLOW, DIM_YELLOW, banner, text, accent), (YELLOW, DIM_YELLOW))

    def test_dark_colors_are_used_when_no_team_color_looks_lit(self):
        # nothing on this team is both bright and contrasting, so the better-contrasting color wins
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, WHITE, BLACK, GUARDIANS_TEXT)
        self.assertEqual(available, BLACK)

    def test_main_uniform_colors_are_tried_when_the_worn_uniform_has_nothing_lit(self):
        # Braves city connect: white text and a pale red side bar on a light blue banner
        banner = {"r": 127, "g": 179, "b": 236}
        text, accent = WHITE, {"r": 241, "g": 37, "b": 60}
        main_accent = {"r": 186, "g": 12, "b": 47}
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, banner, text, accent)
        self.assertEqual(available, WHITE)
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, banner, text, accent, (main_accent, WHITE))
        self.assertEqual(available, main_accent)

    def test_main_uniform_colors_do_not_override_a_lit_color(self):
        available, _ = abs_challenge_colors(
            YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_TEXT, GUARDIANS_RED, (BLACK, WHITE)
        )
        self.assertEqual(available, GUARDIANS_RED)

    def test_white_side_bar_on_an_orange_banner(self):
        orange = {"r": 252, "g": 76, "b": 2}  # Orioles: yellow only reaches about 2.8:1 here
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, orange, BLACK, WHITE)
        self.assertEqual(available, WHITE)

    def test_every_default_team_gets_a_readable_distinguishable_pair(self):
        with open("colors/scoreboard.example.json") as f:
            configured = json.load(f)["abs_challenges"]
        with open("colors/teams.example.json") as f:
            teams = json.load(f)
        checked = 0
        for abbrev, entry in teams.items():
            if not isinstance(entry, dict):
                continue
            uniforms = [entry] + ([entry["city_connect"]] if isinstance(entry.get("city_connect"), dict) else [])
            for colors in uniforms:
                if not all(key in colors for key in ("home", "text", "accent")):
                    continue
                banner = colors["home"]
                fallbacks = (entry["accent"], entry["text"]) if colors is not entry else ()
                available, spent = abs_challenge_colors(
                    configured["available"], configured["used"], banner, colors["text"], colors["accent"], fallbacks
                )
                if available == configured["available"]:
                    continue
                checked += 1
                with self.subTest(team=abbrev, uniform=colors is not entry):
                    # the spent state has to stay clearly different from an available one, unless the team has
                    # no color that reads on its banner at all (the Braves' city connect), where it can't
                    if _contrast(available, banner) >= _MIN_LIT_CONTRAST:
                        self.assertGreaterEqual(_contrast(available, spent), 2.0)
                    lit = [
                        c
                        for c in (colors["accent"], colors["text"], *fallbacks)
                        if _contrast(c, banner) >= _MIN_LIT_CONTRAST and _luminance(c) >= _MIN_LIT_LUMINANCE
                    ]
                    if lit:
                        self.assertIn(available, lit)
        self.assertGreater(checked, 10)


class TestRenderedSquares(unittest.TestCase):
    def render(self, away_banner, away_text, away_accent=BLACK):
        with open("coordinates/w64h32.example.json") as f:
            layout = Layout(json.load(f), 64, 32)
        with open("colors/scoreboard.example.json") as f:
            colors = Color(json.load(f))
        drawn = []

        def draw_line(canvas, x1, y1, x2, y2, color):
            drawn.append((x1, y1, (color.red, color.green, color.blue)))

        team_colors = Color(
            {
                "default": {"home": BLACK, "text": WHITE, "accent": BLACK},
                "away": {"home": away_banner, "text": away_text, "accent": away_accent},
                "home": {"home": NAVY, "text": WHITE, "accent": BLACK},
            }
        )
        away = Team("AWAY", 0, "Away", 0, 0, {}, None, 2)
        home = Team("HOME", 0, "Home", 0, 0, {}, None, 0)
        with mock.patch.object(team_renderer.graphics, "DrawLine", draw_line), mock.patch.object(
            team_renderer.graphics, "DrawText", lambda *a, **k: 0
        ):
            team_renderer.render_team_banner(mock.MagicMock(), layout, team_colors, home, away, True, colors)
        # squares sit in the rightmost two columns; the away squares are in the top rows
        return [c for x, y, c in drawn if x >= 62 and y <= 5]

    def test_away_squares_use_the_side_bar_color_on_a_white_banner(self):
        colors = set(self.render(GUARDIANS_BANNER, GUARDIANS_TEXT, GUARDIANS_RED))
        self.assertIn((204, 0, 46), colors)
        self.assertNotIn((11, 34, 63), colors)
        self.assertNotIn((255, 235, 59), colors)

    def test_away_squares_stay_yellow_on_a_dark_banner(self):
        colors = set(self.render(NAVY, WHITE))
        self.assertIn((255, 235, 59), colors)


if __name__ == "__main__":
    unittest.main()
