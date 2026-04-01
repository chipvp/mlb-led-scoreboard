import time

from driver import graphics

from boards.base import Board
from data import teams as teams_data, status
from utils import center_text_position


class ScoresBoard(Board):
    def render(self, duration):
        games = self.data.schedule.all_games
        if not games:
            return
        per_game = max(duration // len(games), 3)
        for game in games:
            self._show_game(game, per_game)

    def _show_game(self, game, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        end = time.time() + duration

        away_abbr = self._abbr(game["away_id"])
        home_abbr = self._abbr(game["home_id"])
        status_text = self._status_text(game)
        white = graphics.Color(255, 255, 255)
        status_color = colors.graphics_color("final.inning")

        while time.time() < end:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            # Team names (using same coords as the normal game banner)
            away_coords = layout.coords("teams.name.away")
            away_font = layout.font("teams.name.away")
            graphics.DrawText(self.renderer.canvas, away_font["font"],
                              away_coords["x"], away_coords["y"], white, away_abbr)

            home_coords = layout.coords("teams.name.home")
            home_font = layout.font("teams.name.home")
            graphics.DrawText(self.renderer.canvas, home_font["font"],
                              home_coords["x"], home_coords["y"], white, home_abbr)

            # Scores (right-aligned, same position as normal score display)
            if game.get("away_score") is not None:
                self._draw_score(layout, game["away_score"], "away", white)
            if game.get("home_score") is not None:
                self._draw_score(layout, game["home_score"], "home", white)

            # Status ("FINAL", "TOP 7", etc.) using same coords as postgame
            status_coords = layout.coords("final.inning")
            status_font = layout.font("final.inning")
            status_x = center_text_position(status_text, status_coords["x"], status_font["size"]["width"])
            graphics.DrawText(self.renderer.canvas, status_font["font"],
                              status_x, status_coords["y"], status_color, status_text)

            self.renderer.swap_canvas()
            time.sleep(1)

    def _draw_score(self, layout, score, homeaway, color):
        coords = layout.coords(f"teams.runs.{homeaway}").copy()
        font = layout.font(f"teams.runs.{homeaway}")
        score_str = str(score)
        # Right-aligned: coords["x"] is the rightmost pixel (same convention as teams renderer)
        draw_x = coords["x"] - len(score_str) * font["size"]["width"]
        graphics.DrawText(self.renderer.canvas, font["font"], draw_x, coords["y"], color, score_str)

    def _abbr(self, team_id):
        team = teams_data._TEAMS.get(team_id)
        return team["abbr"] if team else "???"

    def _status_text(self, game):
        game_status = game["status"]
        if status.is_complete(game_status) or status.is_fresh(game_status):
            inning = game.get("current_inning", 9)
            text = "FINAL"
            if inning and inning != 9:
                text += f" {inning}"
            return text
        elif status.is_live(game_status):
            state = game.get("inning_state", "")
            inning = game.get("current_inning", "")
            if state and inning:
                prefix = "TOP" if state == "Top" else "BOT"
                return f"{prefix} {inning}"
            return "LIVE"
        else:
            return game_status[:8] if game_status else "TBD"
