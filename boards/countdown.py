import time
from datetime import date

from driver import graphics
from utils import center_text_position
from boards.base import Board
from renderers import scrollingtext


def _resolve_date(date_str):
    """Parse dates in several formats:
    - MM-DD         annual, auto-advances to next year if past
    - MM-DD-YY      one-time, 2-digit year (20YY)
    - YYYY-MM-DD    one-time, full ISO format
    """
    today = date.today()
    parts = date_str.split("-")
    if len(parts) == 2:  # MM-DD
        month, day = int(parts[0]), int(parts[1])
        candidate = date(today.year, month, day)
        if candidate < today:
            candidate = date(today.year + 1, month, day)
        return candidate
    if len(parts) == 3 and len(parts[0]) == 2:  # MM-DD-YY
        month, day, year = int(parts[0]), int(parts[1]), 2000 + int(parts[2])
        return date(year, month, day)
    return date.fromisoformat(date_str)  # YYYY-MM-DD


class CountdownBoard(Board):
    def render(self, duration):
        today = date.today()
        active = sorted(
            [
                (e["label"], (_resolve_date(e["date"]) - today).days)
                for e in self.data.config.countdown_events
                if (_resolve_date(e["date"]) - today).days >= 0
            ],
            key=lambda x: x[1],
        )
        if not active:
            return
        per_event = self.item_duration if self.item_duration is not None else max(duration // len(active), 5)
        for label, days in active:
            self._show_event(label, days, per_event)

    def _show_event(self, label, days, duration):
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors
        end = time.time() + duration
        text_pos = self.renderer.canvas.width

        while time.time() < end:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            if days == 0:
                self._draw_centered(layout, colors, "TODAY!", "countdown.number", "countdown.number")
            else:
                self._draw_centered(layout, colors, str(days), "countdown.number", "countdown.number")
                self._draw_centered(layout, colors, "DAYS UNTIL", "countdown.label", "countdown.label")

            coords = layout.coords("countdown.event")
            font = layout.font("countdown.event")
            color = colors.graphics_color("countdown.event")
            bgcolor_g = colors.graphics_color("default.background")
            text_pos = scrollingtext.render_text(
                self.renderer.canvas,
                coords["x"], coords["y"], coords["width"],
                font, color, bgcolor_g, label, text_pos,
            )

            self.renderer.swap_canvas()
            time.sleep(self.data.config.scrolling_speed)

    def _draw_centered(self, layout, colors, text, coord_key, color_key):
        coords = layout.coords(coord_key)
        font = layout.font(coord_key)
        color = colors.graphics_color(color_key)
        x = center_text_position(text, coords["x"], font["size"]["width"])
        graphics.DrawText(self.renderer.canvas, font["font"], x, coords["y"], color, text)
