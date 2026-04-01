import time

from boards.base import Board
from renderers import scrollingtext


class NewsBoard(Board):
    def render(self, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        end = time.time() + duration
        text_pos = self.renderer.canvas.width

        coords = layout.coords("offday.scrolling_text")
        font = layout.font("offday.scrolling_text")
        color = colors.graphics_color("offday.scrolling_text")
        bgcolor = colors.graphics_color("default.background")

        while time.time() < end:
            bg = colors.color("default.background")
            self.renderer.canvas.Fill(bg["r"], bg["g"], bg["b"])

            ticker_text = self.data.headlines.ticker_string()
            text_pos = scrollingtext.render_text(
                self.renderer.canvas,
                coords["x"],
                coords["y"],
                coords["width"],
                font,
                color,
                bgcolor,
                ticker_text,
                text_pos,
            )

            self.renderer.swap_canvas()
            time.sleep(self.data.config.scrolling_speed)
