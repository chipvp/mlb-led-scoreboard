import unittest
from types import SimpleNamespace

from tests.helpers import make_test_config

LIVE = "In Progress"
PREGAME = "Scheduled"
FINAL = "Final"


def game(status, home="Mets", away="Cubs"):
    return SimpleNamespace(status=lambda: status, home_name=lambda: home, away_name=lambda: away)


def config(rates):
    cfg = make_test_config(led_cols=64, led_rows=32)
    cfg.preferred_teams = ["Cubs", "Angels"]
    cfg.rotation_rates_live = rates["live"]
    cfg.rotation_rates_final = rates["final"]
    cfg.rotation_rates_pregame = rates["pregame"]
    cfg.rotation_rates_live_preferred = rates.get("live_preferred", rates["live"])
    return cfg


RATES = {"live": 15.0, "final": 20.0, "pregame": 25.0, "live_preferred": 60.0}


class TestRotateRateForGame(unittest.TestCase):
    def test_live_preferred_game_uses_preferred_rate(self):
        self.assertEqual(config(RATES).rotate_rate_for_game(game(LIVE, home="Mets", away="Cubs")), 60.0)
        self.assertEqual(config(RATES).rotate_rate_for_game(game(LIVE, home="Angels", away="Mets")), 60.0)

    def test_live_game_without_preferred_team_uses_live_rate(self):
        self.assertEqual(config(RATES).rotate_rate_for_game(game(LIVE, home="Mets", away="Braves")), 15.0)

    def test_pregame_and_final_ignore_preferred_rate(self):
        self.assertEqual(config(RATES).rotate_rate_for_game(game(PREGAME)), 25.0)
        self.assertEqual(config(RATES).rotate_rate_for_game(game(FINAL)), 20.0)

    def test_falls_back_to_live_rate_when_not_configured(self):
        rates = {"live": 15.0, "final": 20.0, "pregame": 25.0}
        self.assertEqual(config(rates).rotate_rate_for_game(game(LIVE)), 15.0)


if __name__ == "__main__":
    unittest.main()
