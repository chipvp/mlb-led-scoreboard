import time

from boards.base import Board
from renderers import standings as standings_renderer


class StandingsBoard(Board):
    def render(self, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        standings = self.data.standings
        end = time.time() + duration

        if not standings.populated():
            return
        if standings.is_postseason() and self.renderer.canvas.width <= 32:
            return

        stat = "w"
        league = "NL"
        update = 1

        while time.time() < end:
            if standings.is_postseason():
                standings_renderer.render_bracket(self.renderer.canvas, layout, colors, standings.leagues[league])
            else:
                standings_renderer.render_standings(
                    self.renderer.canvas, layout, colors, standings.current_standings(), stat
                )

            self.renderer.swap_canvas()

            if standings.is_postseason():
                if update % 20 == 0:
                    league = "AL" if league == "NL" else "NL"
            elif self.renderer.canvas.width == 32 and update % 5 == 0:
                stat = "l" if stat == "w" else "w"
                if stat == "w":
                    standings.advance_to_next_standings()
            elif self.renderer.canvas.width > 32 and update % 10 == 0:
                standings.advance_to_next_standings()

            time.sleep(1)
            update = (update + 1) % 100
