import time

from boards.base import Board
from renderers import offday


class WeatherBoard(Board):
    def render(self, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        end = time.time() + duration
        text_pos = self.renderer.canvas.width

        while time.time() < end:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            text_pos = offday.render_offday_screen(
                self.renderer.canvas,
                layout,
                colors,
                self.data.weather,
                self.data.headlines,
                self.data.config.time_format,
                text_pos,
            )

            self.renderer.swap_canvas()
            time.sleep(self.data.config.scrolling_speed)
