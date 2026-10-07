import json
import unittest
from types import SimpleNamespace
from unittest import mock

from data.config.color import Color
from data.config.layout import Layout
from data.game import Game
from data.scoreboard.linescore import Linescore
from renderers.games import linescore as linescore_renderer


def make_game(innings):
    game = Game.__new__(Game)
    game._current_data = {"liveData": {"linescore": {"innings": innings}}}
    return game


def inning(away, home):
    return {"away": {"runs": away}, "home": {"runs": home}}


class TestInningRuns(unittest.TestCase):
    def test_runs_per_inning(self):
        game = make_game([inning(0, 1), inning(3, 0)])
        self.assertEqual(game.inning_runs("away"), [0, 3])
        self.assertEqual(game.inning_runs("home"), [1, 0])

    def test_missing_runs_are_none(self):
        game = make_game([inning(2, None), {"away": {}, "home": {}}])
        self.assertEqual(game.inning_runs("home"), [None, None])
        self.assertEqual(game.inning_runs("away"), [2, None])

    def test_missing_linescore_is_empty(self):
        game = Game.__new__(Game)
        game._current_data = {}
        self.assertEqual(game.inning_runs("away"), [])

    def test_linescore_wrapper(self):
        linescore = Linescore(make_game([inning(1, 2)]))
        self.assertEqual(linescore.away_innings, [1])
        self.assertEqual(linescore.home_innings, [2])


class TestRenderLinescore(unittest.TestCase):
    def setUp(self):
        with open("coordinates/w64h32.example.json") as f:
            self.layout = Layout(json.load(f), 64, 32)
        with open("colors/scoreboard.example.json") as f:
            self.colors = Color(json.load(f))

    def scoreboard(self, away, home, inning_number=9):
        return SimpleNamespace(
            inning=SimpleNamespace(number=inning_number),
            away_team=SimpleNamespace(abbrev="CHC"),
            home_team=SimpleNamespace(abbrev="LAA"),
            linescore=SimpleNamespace(away_innings=away, home_innings=home),
        )

    def drawn_text(self, scoreboard):
        with mock.patch.object(linescore_renderer, "graphics") as gfx:
            linescore_renderer.render_linescore(mock.MagicMock(), self.layout, self.colors, scoreboard)
        return [call.args[5] for call in gfx.DrawText.call_args_list]

    def test_draws_team_abbrevs_and_runs(self):
        text = self.drawn_text(self.scoreboard([0, 3, 0], [1, 0, None]))
        self.assertIn("CHC", text)
        self.assertIn("LAA", text)
        self.assertIn("3", text)

    def test_ten_or_more_runs_shown_as_x(self):
        text = self.drawn_text(self.scoreboard([10], [0]))
        self.assertIn("X", text)
        self.assertNotIn("10", text)

    def test_unplayed_innings_are_dashes(self):
        text = self.drawn_text(self.scoreboard([1], [None]))
        self.assertIn("-", text)

    def test_disabled_draws_nothing(self):
        self.layout.coords("linescore")["enabled"] = False
        self.assertEqual(self.drawn_text(self.scoreboard([1], [1])), [])


if __name__ == "__main__":
    unittest.main()
