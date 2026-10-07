import datetime
import unittest
from unittest import mock

import data.schedule
from data.schedule import Schedule
from tests.helpers import make_test_config

UTC = datetime.timezone.utc


def game(game_id, first_pitch):
    return {"game_id": game_id, "game_datetime": first_pitch.strftime("%Y-%m-%dT%H:%M:%SZ")}


def make_config(enabled=True, hours=1):
    config = make_test_config(config="tests/data/demo-date-offday", led_cols=32, led_rows=32)
    config.show_yesterday_scores_enabled = enabled
    config.show_yesterday_scores_hours_before = hours
    return config


def make_schedule(config, fetch):
    with mock.patch.object(Schedule, "_Schedule__fetch_games", fetch):
        with mock.patch.object(Schedule, "_Schedule__filter_games", lambda self, games: (0, list(games))):
            return Schedule(config)


class TestShouldShowYesterday(unittest.TestCase):
    def check(self, config, todays_games):
        schedule = Schedule.__new__(Schedule)
        schedule.config = config
        return schedule._Schedule__should_show_yesterday(todays_games)

    def test_disabled(self):
        soon = datetime.datetime.now(UTC) + datetime.timedelta(hours=5)
        self.assertFalse(self.check(make_config(enabled=False), [game(1, soon)]))

    def test_no_games_today_keeps_offday_screen(self):
        self.assertFalse(self.check(make_config(), []))

    def test_before_cutoff(self):
        first_pitch = datetime.datetime.now(UTC) + datetime.timedelta(hours=5)
        self.assertTrue(self.check(make_config(hours=1), [game(1, first_pitch)]))

    def test_after_cutoff(self):
        first_pitch = datetime.datetime.now(UTC) + datetime.timedelta(minutes=30)
        self.assertFalse(self.check(make_config(hours=1), [game(1, first_pitch)]))

    def test_cutoff_uses_earliest_game(self):
        now = datetime.datetime.now(UTC)
        games = [game(1, now + datetime.timedelta(hours=8)), game(2, now + datetime.timedelta(minutes=10))]
        self.assertFalse(self.check(make_config(hours=1), games))


class TestUpdateUsesYesterday(unittest.TestCase):
    def fetch_for(self, todays, yesterdays, fetched_dates):
        def fetch(self_, date):
            fetched_dates.append(date)
            return (todays if len(fetched_dates) == 1 else yesterdays), 0

        return fetch

    def test_swaps_in_yesterdays_games_before_cutoff(self):
        now = datetime.datetime.now(UTC)
        todays = [game("today", now + datetime.timedelta(hours=5))]
        yesterdays = [game("yesterday", now - datetime.timedelta(hours=19))]
        dates = []
        schedule = make_schedule(make_config(), self.fetch_for(todays, yesterdays, dates))

        self.assertEqual(len(dates), 2)
        self.assertEqual(dates[0] - dates[1], datetime.timedelta(days=1))
        self.assertEqual([g["game_id"] for g in schedule._games], ["yesterday"])

    def test_keeps_todays_games_when_disabled(self):
        now = datetime.datetime.now(UTC)
        todays = [game("today", now + datetime.timedelta(hours=5))]
        dates = []
        schedule = make_schedule(make_config(enabled=False), self.fetch_for(todays, [], dates))

        self.assertEqual(len(dates), 1)
        self.assertEqual([g["game_id"] for g in schedule._games], ["today"])

    def test_keeps_todays_games_if_yesterday_fetch_fails(self):
        now = datetime.datetime.now(UTC)
        todays = [game("today", now + datetime.timedelta(hours=5))]
        calls = []

        def fetch(self_, date):
            calls.append(date)
            return (todays, 0) if len(calls) == 1 else ([], len(self_.config.leagues))

        schedule = make_schedule(make_config(), fetch)
        self.assertEqual([g["game_id"] for g in schedule._games], ["today"])


if __name__ == "__main__":
    unittest.main()
