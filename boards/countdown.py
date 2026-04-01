import re
import time
from datetime import date

from driver import graphics
from utils import center_text_position
from boards.base import Board
from renderers import scrollingtext

_NAMED_COLORS = {
    "red":     (220,  50,  50),
    "green":   (  0, 200, 100),
    "blue":    ( 50, 100, 255),
    "yellow":  (255, 220,  50),
    "orange":  (255, 165,   0),
    "pink":    (255, 105, 180),
    "purple":  (180, 100, 255),
    "cyan":    (  0, 220, 220),
    "magenta": (220,   0, 220),
    "white":   (255, 255, 255),
}


def _parse_segments(label, default_color):
    """Parse a Rich-style tagged label into a list of (text, Color) segments.

    Supported tag formats:
      [red]   — named color (see _NAMED_COLORS)
      [#rrggbb] — hex color
      [/]     — close tag, resets to default_color

    Example:
      "[red]Milo's[/] [white]Bday[/]"  →  [("Milo's", red), (" ", default), ("Bday", white)]
    """
    segments = []
    current = default_color
    for part in re.split(r'(\[[^\]]*\])', label):
        if part.startswith('[') and part.endswith(']'):
            tag = part[1:-1].strip()
            if tag.startswith('/'):
                current = default_color
            elif tag.startswith('#') and len(tag) == 7:
                h = tag[1:]
                current = graphics.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            elif tag.lower() in _NAMED_COLORS:
                r, g, b = _NAMED_COLORS[tag.lower()]
                current = graphics.Color(r, g, b)
        elif part:
            segments.append((part, current))
    return segments or [('', default_color)]


def _render_scrolling_segments(canvas, x, y, width, font, bg_color, segments, scroll_pos):
    """Render a list of (text, Color) segments with horizontal scrolling.

    Works like scrollingtext.render_text but supports per-segment colors.
    Returns total pixel width of the text (for scroll position tracking), or 0 if static.
    """
    w = font["size"]["width"]
    full_text = ''.join(t for t, _ in segments)
    total_width = w * len(full_text)

    if total_width <= width:
        # Text fits — center it
        draw_x = center_text_position(full_text, abs(width // 2) + x, w)
        for text, color in segments:
            graphics.DrawText(canvas, font["font"], draw_x, y, color, text)
            draw_x += len(text) * w
        return 0

    # Draw each segment at its scroll-offset position
    cur_x = scroll_pos
    for text, color in segments:
        graphics.DrawText(canvas, font["font"], cur_x, y, color, text)
        cur_x += len(text) * w

    # Mask edges with bg_color lines so text clips cleanly
    top = y + 1
    bottom = top - font["size"]["height"]
    for xi in range(0, w):
        graphics.DrawLine(canvas, x - xi - 1, top, x - xi - 1, bottom, bg_color)
        graphics.DrawLine(canvas, x + width + xi, top, x + width + xi, bottom, bg_color)

    return total_width


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
        default_color = colors.graphics_color("countdown.event")
        bg_color = colors.graphics_color("default.background")
        segments = _parse_segments(label, default_color)

        while time.time() < end:
            bgcolor = colors.color("default.background")
            self.renderer.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

            if days == 0:
                self._draw_centered(layout, "TODAY!", "countdown.number", colors.graphics_color("countdown.number"))
            else:
                self._draw_centered(layout, str(days), "countdown.number", colors.graphics_color("countdown.number"))
                self._draw_centered(layout, "DAYS UNTIL", "countdown.label", colors.graphics_color("countdown.label"))

            coords = layout.coords("countdown.event")
            font = layout.font("countdown.event")
            total_width = _render_scrolling_segments(
                self.renderer.canvas,
                coords["x"], coords["y"], coords["width"],
                font, bg_color, segments, text_pos,
            )
            text_pos -= 1
            if text_pos + total_width < -10:
                text_pos = self.renderer.canvas.width

            self.renderer.swap_canvas()
            time.sleep(self.data.config.scrolling_speed)

    def _draw_centered(self, layout, text, coord_key, color):
        coords = layout.coords(coord_key)
        font = layout.font(coord_key)
        x = center_text_position(text, coords["x"], font["size"]["width"])
        graphics.DrawText(self.renderer.canvas, font["font"], x, coords["y"], color, text)
