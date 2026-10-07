import datetime
import time
from collections import defaultdict
from typing import Any, Optional
from math import ceil

import statsapi
import wpbl_statsapi_adaptor

from bullpen.logging import LOGGER
from data.game import Game
from bullpen.api import UpdateStatus
from data.utils.circular_queue import CircularQueue
from data.config import Config

GAMES_REFRESH_RATE = 15


class Schedule:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.starttime = time.time()
        self.current_idx = 0

        delay_required = ceil(self.config.sync_delay_seconds / GAMES_REFRESH_RATE)

        self._data_wait_queue = CircularQueue(delay_required + 1)
        # the (filtered) schedule
        self._games: list[dict[str, Any]] = []
        self.priority = 0
        self.update(True)

    def update(self, force=False) -> UpdateStatus:
        if force or self.__should_update():
            date = self.config.parse_today()
            LOGGER.debug("Updating schedule for %s", date.strftime("%Y-%m-%d"))
            self.starttime = time.time()
            all_games, exceptions = self.__fetch_games(date)

            if exceptions == len(self.config.leagues):
                return UpdateStatus.FAIL

            if self.__should_show_yesterday(all_games):
                yesterday = date - datetime.timedelta(days=1)
                LOGGER.debug("Showing yesterday's scores (%s)", yesterday.strftime("%Y-%m-%d"))
                yesterdays_games, exceptions = self.__fetch_games(yesterday)
                if exceptions < len(self.config.leagues):
                    all_games = yesterdays_games

            priority, games = self.__filter_games(all_games)
            games.sort(key=lambda g: g["game_datetime"])

            if priority > self.priority:
                # going up a priority level should never be delayed
                self._data_wait_queue.clear()
            self._data_wait_queue.push((priority, games))

            priority, games = self._data_wait_queue.peek()
            if len(games) > 0:
                self.current_idx %= len(games)
            else:
                self.current_idx = 0

            self._games = games
            self.priority = priority
            LOGGER.debug(
                "Schedule updated with %d games (priority %d) (current delay %d)",
                len(self._games),
                priority,
                self.current_delay(),
            )
            return UpdateStatus.SUCCESS

        return UpdateStatus.DEFERRED

    def __fetch_games(self, date) -> tuple[list[dict[str, Any]], int]:
        """Fetch the schedule for every league. Returns the games and the number of leagues that failed."""
        games = []
        exceptions = 0
        for league in self.config.leagues:
            try:
                league_games = league.statsapi.schedule(date.strftime("%Y-%m-%d"), **league.schedule_params)
                games.extend([g | {"league": league} for g in league_games])
            except Exception:
                LOGGER.exception(f"Networking error while refreshing {league.name} schedule")
                exceptions += 1
        return games, exceptions

    def __should_show_yesterday(self, todays_games) -> bool:
        """
        Whether to show yesterday's games instead of today's. Only until the configured number of hours
        before the first pitch. A day with no games is never replaced, so a full league off-day still
        shows the normal off-day screen rather than yesterday forever.
        """
        if not self.config.show_yesterday_scores_enabled or not todays_games:
            return False

        first_pitch = min(
            datetime.datetime.fromisoformat(game["game_datetime"].replace("Z", "+00:00")) for game in todays_games
        )
        cutoff = first_pitch - datetime.timedelta(hours=self.config.show_yesterday_scores_hours_before)
        return datetime.datetime.now(datetime.timezone.utc) < cutoff

    def __should_update(self):
        endtime = time.time()
        return endtime - self.starttime >= GAMES_REFRESH_RATE

    def current_delay(self):
        return (len(self._data_wait_queue) - 1) * GAMES_REFRESH_RATE

    def num_games(self):
        return len(self._games)

    def next_game(self, unless: Optional[Game] = None) -> Optional[Game]:
        self.current_idx = self.__next_game_index()
        return self.__current_game(unless)

    def __next_game_index(self):
        counter = self.current_idx + 1
        if counter >= len(self._games):
            counter = 0
        if counter != self.current_idx:
            LOGGER.debug("Schedule: going to game index %d", counter)
        return counter

    def __current_game(self, unless: Optional[Game] = None) -> Optional[Game]:
        try:
            scheduled_game = self._games[self.current_idx]
            if unless and scheduled_game["game_id"] == unless.game_id:
                return unless
            return Game.from_scheduled(scheduled_game, self.config)
        except IndexError:
            return None

    def __filter_games(self, all_games: list) -> tuple[int, list]:
        """
        Returns the highest priority level and the games that match that level,
        for the given list of games and current time.
        """
        priorities: defaultdict[int, list] = defaultdict(list)
        highest = 0

        for rule in self.config.rotation_time_rules:
            priority = rule.matches(datetime.datetime.now())
            if priority:
                highest = max(highest, priority)

        for game in all_games:
            seen = set()
            for rule in self.config.rotation_game_rules:
                if rule.priority() < highest:
                    continue
                priority, passive = rule.matches(game)
                if priority:
                    if priority not in seen:
                        priorities[priority].append(game)
                        seen.add(priority)

                    if not passive:
                        highest = max(highest, priority)

        return highest, priorities[highest]
