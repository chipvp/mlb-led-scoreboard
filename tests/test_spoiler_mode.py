import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import spoiler_mode_manager as manager
from data.config import _preferred_team_names
from renderers.games import game as game_renderer
from renderers.games import postgame as postgame_renderer


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class TestSpoilerModeManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.shared = Path(self.tmp.name) / "spoiler"
        self.local = Path(self.tmp.name) / "local"
        self.clock = FakeClock()
        patches = [
            mock.patch.dict("os.environ", {"MLB_PANEL_SPOILER": str(self.shared)}),
            mock.patch.object(manager, "FALLBACK_SPOILER_FILE", self.local),
            mock.patch.object(manager, "_clock", self.clock),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        manager.reset()
        self.addCleanup(manager.reset)

    def tick(self, seconds=1.5):
        self.clock.now += seconds

    def test_off_by_default_with_no_files(self):
        self.assertFalse(manager.is_spoiler_free_for_team("Cubs"))
        self.assertFalse(manager.is_spoiler_mode())

    def test_team_switch_only_affects_that_team(self):
        self.shared.write_text("Cubs=on\nAngels=off\n__global__=off\n")
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.assertTrue(manager.is_team_spoiler_mode("Cubs"))
        self.assertFalse(manager.is_spoiler_free_for_team("Angels"))

    def test_global_switch_affects_every_team(self):
        self.shared.write_text("__global__=on\n")
        self.assertTrue(manager.is_spoiler_mode())
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.assertTrue(manager.is_spoiler_free_for_team("Angels"))

    def test_reread_at_most_once_a_second(self):
        self.shared.write_text("Cubs=on\n")
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.shared.write_text("Cubs=off\n")
        self.tick(0.5)
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.tick(0.6)
        self.assertFalse(manager.is_spoiler_free_for_team("Cubs"))

    def test_read_error_keeps_last_good(self):
        self.shared.write_text("Cubs=on\n")
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.shared.unlink()
        self.shared.mkdir()  # exists but cannot be read as a file (OSError, not missing)
        self.tick()
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))

    def test_falls_back_to_local_file_only_when_shared_is_missing(self):
        self.local.write_text("Cubs=on\n")
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))
        self.shared.write_text("Cubs=off\n")
        self.tick()
        self.assertFalse(manager.is_spoiler_free_for_team("Cubs"))

    def test_bom_is_tolerated(self):
        self.shared.write_bytes(b"\xef\xbb\xbfCubs=on\n")
        self.assertTrue(manager.is_spoiler_free_for_team("Cubs"))


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
