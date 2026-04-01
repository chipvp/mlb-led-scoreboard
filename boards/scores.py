import time

from driver import graphics
from utils import center_text_position
from boards.base import Board
from data import status as game_status
from data import teams as teams_data
from data.scoreboard.team import Team
from renderers.games import teams as teams_renderer


def _abbr(team_id):
    team = teams_data._TEAMS.get(team_id, {})
    return team.get("abbr", "???")


def _status_text(game):
    s = game.get("status", "")
    if game_status.is_complete(s) or game_status.is_fresh(s):
        inning = game.get("current_inning")
        return f"FINAL/{inning}" if inning and inning != 9 else "FINAL"
    if game_status.is_live(s):
        state = game.get("inning_state", "")
        inning = game.get("current_inning", "")
        if state and inning:
            prefix = "TOP" if state == "Top" else "BOT"
            return f"{prefix} {inning}"
        return "LIVE"
    if game_status.is_pregame(s):
        return game.get("game_datetime", "PRE")[-8:-3] or "PRE"  # "HH:MM" from datetime string
    return s[:8] if s else "TBD"


class ScoresBoard(Board):
    def render(self, duration):
        games = self.data.schedule.all_games
        if not games:
            return
        per_game = self.item_duration if self.item_duration is not None else max(duration // len(games), 3)
        for game in games:
            self._show_game(game, per_game)

    def _show_game(self, game, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        team_colors = self.data.config.team_colors
        end = time.time() + duration

        away = Team(_abbr(game["away_id"]), game.get("away_score", 0),
                    game.get("away_name", ""), 0, 0, "", None)
        home = Team(_abbr(game["home_id"]), game.get("home_score", 0),
                    game.get("home_name", ""), 0, 0, "", None)
        show_score = not game_status.is_pregame(game.get("status", ""))
        status_text = _status_text(game)

        status_coords = layout.coords("final.inning")
        status_font = layout.font("final.inning")
        status_color = colors.graphics_color("final.inning")

        while time.time() < end:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            teams_renderer.render_team_banner(
                self.renderer.canvas, layout, team_colors,
                home, away,
                self.data.config.full_team_names,
                self.data.config.short_team_names_for_runs_hits,
                show_score=show_score,
            )

            x = center_text_position(status_text, status_coords["x"], status_font["size"]["width"])
            graphics.DrawText(
                self.renderer.canvas, status_font["font"],
                x, status_coords["y"], status_color, status_text,
            )

            self.renderer.swap_canvas()
            time.sleep(self.data.config.scrolling_speed)
