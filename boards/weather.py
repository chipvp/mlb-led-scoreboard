import time

from boards.base import Board
from renderers import offday


class WeatherBoard(Board):
    def render(self, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        text_pos = self.renderer.canvas.width

        while True:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            total_width = offday.render_offday_screen(
                self.renderer.canvas,
                layout,
                colors,
                self.data.weather,
                self.data.headlines,
                self.data.config.time_format,
                text_pos,
            )

            text_pos -= 1
            if text_pos + total_width < -10:
                break

            self.renderer.swap_canvas()
            time.sleep(self.data.config.scrolling_speed)
