import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import spoiler_mode_manager as manager
from data.config import _preferred_team_names
from renderers.games import game as game_renderer
from renderers.games import postgame as postgame_renderer


class TestSpoilerModeManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patches = [
            mock.patch.object(manager, "_STATE_FILE", Path(self.tmp.name) / "state"),
            mock.patch.object(manager, "_state", {}),
            mock.patch("builtins.print"),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_off_by_default(self):
        self.assertFalse(manager.is_spoiler_free_for_team("Cubs"))

    def test_team_switch_only_affects_that_team(self):
        manager.set_team_spoiler_mode("Cubs", True)
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.assertFalse(manager.is_spoiler_free_for_team("Angels"))

    def test_global_switch_affects_every_team(self):
        manager.set_spoiler_mode(True)
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.assertTrue(manager.is_spoiler_free_for_team("Angels"))

    def test_state_round_trips_through_file(self):
        manager.set_team_spoiler_mode("Cubs", True)
        manager.set_spoiler_mode(False)
        self.assertEqual(manager._load_state(), {"Cubs": True, manager._GLOBAL_KEY: False})


class TestPreferredTeamNames(unittest.TestCase):
    def test_collects_game_rule_teams_in_order_without_duplicates(self):
        screens = [
            {"kind": "game", "priority": 2, "teams": ["Cubs", "Angels"]},
            {"kind": "secondary_game", "with_priority": 1, "teams": ["Angels", "Mets"]},
            {"kind": "news", "seconds": 10, "with_priority": 0},
            {"kind": "game", "priority": 1},
        ]
        self.assertEqual(_preferred_team_names(screens), ["Cubs", "Angels", "Mets"])

    def test_no_team_rules(self):
        self.assertEqual(_preferred_team_names([{"kind": "game", "priority": 1}]), [])


class TestSpoilerFreeRenderers(unittest.TestCase):
    def test_live_game_draws_nothing(self):
        canvas = mock.MagicMock()
        result = game_renderer.render_live_game(canvas, None, None, None, 42, 0, spoiler_free=True)
        self.assertEqual(result, 42)
        self.assertEqual(canvas.method_calls, [])

    def test_postgame_draws_nothing(self):
        canvas = mock.MagicMock()
        result = postgame_renderer.render_postgame(canvas, None, None, None, None, 7, True, False, spoiler_free=True)
        self.assertEqual(result, 7)
        self.assertEqual(canvas.method_calls, [])


if __name__ == "__main__":
    unittest.main()
