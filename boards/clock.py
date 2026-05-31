import time

from driver import graphics
from utils import center_text_position
from data.time_formats import TIME_FORMAT_12H, os_datetime_format
from boards.base import Board


class ClockBoard(Board):
    def render(self, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        time_format = self.data.config.time_format
        end = time.time() + duration

        time_fmt = "{}:%M{}".format(time_format, "%p" if time_format == TIME_FORMAT_12H else "")
        date_fmt = os_datetime_format("%a %b %-d")

        while time.time() < end:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            # Time (e.g. "3:45PM")
            time_text = time.strftime(time_fmt)
            coords = layout.coords("clock.time")
            font = layout.font("clock.time")
            color = colors.graphics_color("clock.time")
            x = center_text_position(time_text, coords["x"], font["size"]["width"])
            graphics.DrawText(self.renderer.canvas, font["font"], x, coords["y"], color, time_text)

            # Date (e.g. "Mon Mar 31")
            date_text = time.strftime(date_fmt)
            coords = layout.coords("clock.date")
            font = layout.font("clock.date")
            color = colors.graphics_color("clock.date")
            x = center_text_position(date_text, coords["x"], font["size"]["width"])
            graphics.DrawText(self.renderer.canvas, font["font"], x, coords["y"], color, date_text)

            self.renderer.swap_canvas()
            time.sleep(1)
