from data.config.layout import Layout
from data.scoreboard.team import Team
from renderers.games.teams import can_use_full_team_names, team_display_name

import unittest, string, random

WIDTH = 32
HEIGHT = 32


def make_layout(full=False, shorten_team_name_on_high_line_score=False):
    return Layout(
        {
            "teams": {
                "name": {"full": full},
                "line_score": {"shorten_team_name_on_high_line_score": shorten_team_name_on_high_line_score},
                "record": {},
            },
            "defaults": {"font_name": "4x6"},
        },
        WIDTH,
        HEIGHT,
    )


def make_team(
    abbrev="".join(random.choice(string.ascii_uppercase) for _ in range(3)),
    runs=0,
    name=None,
    hits=0,
    errors=0,
    record="0-0",
    special_uniform=None,
    abs_challenges=2,
):
    if name is None:
        name = f"Test {abbrev}"

    return Team(abbrev, runs, name, hits, errors, record, special_uniform, abs_challenges)


class TestCanUseFullTeamNames(unittest.TestCase):

    def test_global_setting_disabled(self):
        layout = make_layout()
        teams = [make_team(), make_team()]

        self.assertFalse(can_use_full_team_names(layout, teams))

    def test_global_setting_disabled_shorten_disabled_with_10_hits(self):
        layout = make_layout()
        teams = [make_team(hits=10), make_team()]

        self.assertFalse(can_use_full_team_names(layout, teams))

    def test_global_setting_enabled_shorten_disabled_with_10_hits(self):
        layout = make_layout(full=True)
        teams = [make_team(hits=10), make_team()]

        self.assertTrue(can_use_full_team_names(layout, teams))

    def test_settings_enabled_with_10_hits(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        teams = [make_team(hits=10), make_team()]

        self.assertFalse(can_use_full_team_names(layout, teams))

    def test_settings_enabled_with_10_runs(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        teams = [make_team(runs=10), make_team()]

        self.assertFalse(can_use_full_team_names(layout, teams))

    def test_settings_enabled_with_10_errors(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        # A very bad day at the ballpark
        teams = [make_team(errors=10), make_team()]

        self.assertFalse(can_use_full_team_names(layout, teams))

    def test_settings_enabled_with_rhe_less_than_10(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        teams = [make_team(runs=5, hits=5, errors=5), make_team(runs=5, hits=5, errors=5)]

        self.assertTrue(can_use_full_team_names(layout, teams))


class TestTeamDisplayName(unittest.TestCase):
    def make(self, name, short, **kwargs):
        team = make_team(name=name, **kwargs)
        team.short_name = short
        return team

    def test_full_names_disabled_uses_abbrev(self):
        layout = make_layout(shorten_team_name_on_high_line_score=True)
        team = self.make("Yankees", "Yanks", abbrev="NYY", runs=12, hits=12)
        self.assertEqual(team_display_name(layout, team), "NYY")

    def test_low_line_score_uses_full_name(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        team = self.make("Yankees", "Yanks", runs=5, hits=9)
        self.assertEqual(team_display_name(layout, team), "Yankees")

    def test_seven_char_name_needs_runs_and_hits(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        self.assertEqual(team_display_name(layout, self.make("Yankees", "Yanks", runs=10, hits=5)), "Yankees")
        self.assertEqual(team_display_name(layout, self.make("Yankees", "Yanks", runs=10, hits=10)), "Yanks")

    def test_long_name_shortens_on_runs_or_hits(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        self.assertEqual(team_display_name(layout, self.make("Cardinals", "Cards", hits=10)), "Cards")
        self.assertEqual(team_display_name(layout, self.make("Cardinals", "Cards", runs=10)), "Cards")

    def test_short_name_never_shortened(self):
        layout = make_layout(full=True, shorten_team_name_on_high_line_score=True)
        self.assertEqual(team_display_name(layout, self.make("Cubs", "Cubs", runs=12, hits=15)), "Cubs")

    def test_shorten_disabled_keeps_full_name(self):
        layout = make_layout(full=True)
        self.assertEqual(team_display_name(layout, self.make("Cardinals", "Cards", runs=12)), "Cardinals")
