import time

from boards.base import Board
from data.game import Game


class ScoresBoard(Board):
    def render(self, duration):
        games = self.data.schedule.all_games
        if not games:
            return
        per_game = max(duration // len(games), 3)
        for scheduled_game in games:
            game = Game.from_scheduled(
                scheduled_game,
                self.data.config.preferred_game_delay_multiplier,
                self.data.config.api_refresh_rate,
            )
            if game is None:
                continue
            end = time.time() + per_game
            while time.time() < end:
                self.renderer.draw_game(game)
                time.sleep(self.data.config.scrolling_speed)
