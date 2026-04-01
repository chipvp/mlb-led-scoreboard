import time

from boards.base import Board
from data.game import Game


class ScoresBoard(Board):
    def render(self, duration):
        games = self.data.schedule.all_games
        if not games:
            return
        per_game = self.item_duration if self.item_duration is not None else max(duration // len(games), 3)
        for scheduled_game in games:
            game = Game.from_scheduled(
                scheduled_game,
                self.data.config.preferred_game_delay_multiplier,
                self.data.config.api_refresh_rate,
            )
            if game is None:
                continue
            self.renderer.scrolling_text_pos = self.renderer.canvas.width
            self.renderer.data.scrolling_finished = False
            end = time.time() + per_game
            while True:
                done = self.renderer.draw_game(game)
                time.sleep(self.data.config.scrolling_speed)
                if done or time.time() > end:
                    break
