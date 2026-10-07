import unittest
from types import SimpleNamespace
from unittest import mock

from renderers.games import postgame as postgame_renderer


def make_postgame():
    return SimpleNamespace(
        winning_pitcher="Smith",
        winning_pitcher_wins=3,
        winning_pitcher_losses=1,
        losing_pitcher="Jones",
        losing_pitcher_wins=2,
        losing_pitcher_losses=4,
        save_pitcher=None,
        save_pitcher_saves=0,
        recap_blurb=None,
        series_status="",
    )


def scroll_text_for(inning):
    layout = mock.MagicMock()
    layout.coords.return_value = {"x": 0, "y": 0, "width": 10}
    colors = mock.MagicMock()
    scoreboard = SimpleNamespace(inning=SimpleNamespace(number=inning))
    with mock.patch.object(postgame_renderer, "scrolling_text") as scroll:
        postgame_renderer._render_decision_scroll(
            mock.MagicMock(), layout, colors, make_postgame(), scoreboard, 0, False, False
        )
    return scroll.call_args.args[-2]


class TestDecisionScroll(unittest.TestCase):
    def test_regulation_game_has_no_prefix(self):
        self.assertTrue(scroll_text_for(9).startswith("W: Smith"))

    def test_extra_innings_prefixes_final_n(self):
        self.assertTrue(scroll_text_for(11).startswith("Final/11   W: Smith"))
