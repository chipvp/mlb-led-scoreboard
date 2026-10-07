import json
import unittest
from unittest import mock

from data.config.color import Color
from data.config.layout import Layout
from data.scoreboard.team import Team
from renderers.games import teams as team_renderer
from renderers.games.teams import _contrast, abs_challenge_colors

YELLOW = {"r": 255, "g": 235, "b": 59}
DIM_YELLOW = {"r": 100, "g": 90, "b": 22}
GUARDIANS_BANNER = {"r": 227, "g": 227, "b": 239}
GUARDIANS_TEXT = {"r": 204, "g": 0, "b": 46}
NAVY = {"r": 0, "g": 20, "b": 70}
WHITE = {"r": 255, "g": 255, "b": 255}
BLACK = {"r": 0, "g": 0, "b": 0}


class TestAbsChallengeColors(unittest.TestCase):
    def test_contrast_ratio_extremes(self):
        self.assertAlmostEqual(_contrast(BLACK, WHITE), 21.0, places=1)
        self.assertAlmostEqual(_contrast(WHITE, WHITE), 1.0)

    def test_configured_colors_kept_on_a_dark_banner(self):
        self.assertEqual(abs_challenge_colors(YELLOW, DIM_YELLOW, NAVY, WHITE), (YELLOW, DIM_YELLOW))

    def test_yellow_on_a_white_banner_falls_back_to_the_team_text_color(self):
        available, spent = abs_challenge_colors(YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_TEXT)
        self.assertEqual(available, GUARDIANS_TEXT)
        self.assertGreaterEqual(_contrast(available, GUARDIANS_BANNER), 3.0)

    def test_spent_challenge_is_dimmer_than_available_but_not_the_banner_color(self):
        available, spent = abs_challenge_colors(YELLOW, DIM_YELLOW, GUARDIANS_BANNER, GUARDIANS_TEXT)
        self.assertNotEqual(spent, available)
        self.assertNotEqual(spent, GUARDIANS_BANNER)
        self.assertLess(_contrast(spent, GUARDIANS_BANNER), _contrast(available, GUARDIANS_BANNER))

    def test_keeps_configured_colors_when_the_text_color_is_no_better(self):
        # yellow on a light banner with an equally poor text color: nothing to gain by swapping
        banner, text = {"r": 250, "g": 250, "b": 250}, {"r": 245, "g": 245, "b": 245}
        self.assertEqual(abs_challenge_colors(YELLOW, DIM_YELLOW, banner, text), (YELLOW, DIM_YELLOW))

    def test_black_text_on_an_orange_banner(self):
        orange = {"r": 252, "g": 76, "b": 2}  # Orioles: yellow only reaches about 2.8:1 here
        available, _ = abs_challenge_colors(YELLOW, DIM_YELLOW, orange, BLACK)
        self.assertEqual(available, BLACK)


class TestRenderedSquares(unittest.TestCase):
    def render(self, away_banner, away_text):
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
                "away": {"home": away_banner, "text": away_text, "accent": BLACK},
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

    def test_away_squares_use_the_team_color_on_a_white_banner(self):
        colors = set(self.render(GUARDIANS_BANNER, GUARDIANS_TEXT))
        self.assertIn((204, 0, 46), colors)
        self.assertNotIn((255, 235, 59), colors)

    def test_away_squares_stay_yellow_on_a_dark_banner(self):
        colors = set(self.render(NAVY, WHITE))
        self.assertIn((255, 235, 59), colors)


if __name__ == "__main__":
    unittest.main()
