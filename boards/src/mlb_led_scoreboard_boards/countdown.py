import re
import time
from datetime import date, datetime
from typing import Optional

import bullpen.api as api
from bullpen.logging import LOGGER
from bullpen.util import center_text_position

DEFAULT_ITEM_DURATION = 10
REFRESH_SECONDS = 60

NAMED_COLORS = {
    "red": (220, 50, 50),
    "green": (0, 200, 100),
    "blue": (50, 100, 255),
    "yellow": (255, 220, 50),
    "orange": (255, 165, 0),
    "pink": (255, 105, 180),
    "purple": (180, 100, 255),
    "cyan": (0, 220, 220),
    "magenta": (220, 0, 220),
    "white": (255, 255, 255),
}


def parse_segments(graphics, label, default_color):
    """Parse a Rich-style tagged label into a list of (text, Color) segments.

    Supported tags:
      [red]     named color (see NAMED_COLORS)
      [#rrggbb] hex color
      [/]       close tag, resets to default_color

    Example: "[red]Milo's[/] [white]Bday[/]" -> [("Milo's", red), (" ", default), ("Bday", white)]
    """
    segments = []
    current = default_color
    for part in re.split(r"(\[[^\]]*\])", label):
        if part.startswith("[") and part.endswith("]"):
            tag = part[1:-1].strip()
            if tag.startswith("/"):
                current = default_color
            elif tag.startswith("#") and len(tag) == 7:
                h = tag[1:]
                current = graphics.Color(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            elif tag.lower() in NAMED_COLORS:
                current = graphics.Color(*NAMED_COLORS[tag.lower()])
        elif part:
            segments.append((part, current))
    return segments or [("", default_color)]


def resolve_date(date_str: str, today: date) -> date:
    """Parse an event date in one of these formats:
    - MM-DD       annual, rolls over to next year once it has passed
    - MM-DD-YY    one-time, 2-digit year (20YY)
    - YYYY-MM-DD  one-time, full ISO format
    """
    parts = date_str.split("-")
    if len(parts) == 2:
        month, day = int(parts[0]), int(parts[1])
        candidate = date(today.year, month, day)
        if candidate < today:
            candidate = date(today.year + 1, month, day)
        return candidate
    if len(parts) == 3 and len(parts[0]) == 2:
        month, day, year = int(parts[0]), int(parts[1]), 2000 + int(parts[2])
        return date(year, month, day)
    return date.fromisoformat(date_str)


class Config(api.PluginConfig):
    def __init__(self, config: api.MLBConfig) -> None:
        self.parse_today = config.parse_today
        self.scrolling_speed = config.scrolling_speed
        self.events = config.plugin_config.get("events", [])
        self.item_duration = config.plugin_config.get("item_duration", DEFAULT_ITEM_DURATION)


class CountdownData(api.PluginData):
    def __init__(self, config: Config) -> None:
        self.config = config
        self.active: list[tuple[str, int]] = []
        self._updated = 0.0
        self.update(True)

    def update(self, force: bool = False) -> api.UpdateStatus:
        if not force and time.monotonic() - self._updated < REFRESH_SECONDS:
            return api.UpdateStatus.DEFERRED
        self._updated = time.monotonic()

        today = self.config.parse_today()
        if isinstance(today, datetime):
            today = today.date()

        active = []
        for event in self.config.events:
            try:
                days = (resolve_date(event["date"], today) - today).days
            except (KeyError, ValueError):
                LOGGER.warning("Skipping countdown event with a missing or invalid date: %s", event)
                continue
            if days >= 0:
                active.append((event.get("label", ""), days))

        # soonest first
        self.active = sorted(active, key=lambda event: event[1])
        return api.UpdateStatus.SUCCESS


class Renderer(api.PluginRenderer[CountdownData]):
    def __init__(self, config: Config, layout: api.Layout, colors: api.Color) -> None:
        self.config = config
        self.layout = layout
        self.colors = colors
        self.reset()

    def reset(self):
        self._index = 0
        self._shown_at: Optional[float] = None
        self._scroll_x: Optional[int] = None

    def wait_time(self) -> float:
        return self.config.scrolling_speed

    def can_render(self, data: CountdownData) -> bool:
        return bool(data.active)

    def render(self, data, canvas, graphics, scrolling_text_pos):
        now = time.monotonic()
        if self._shown_at is None:
            self._shown_at = now
            self._scroll_x = canvas.width
        elif now - self._shown_at >= self.config.item_duration:
            self._index += 1
            self._shown_at = now
            self._scroll_x = canvas.width
        label, days = data.active[self._index % len(data.active)]

        bgcolor = self.colors.color("default.background")
        canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

        if days == 0:
            self.__draw_centered(canvas, graphics, "TODAY!", "countdown.number")
        else:
            self.__draw_centered(canvas, graphics, str(days), "countdown.number")
            self.__draw_centered(canvas, graphics, "DAYS UNTIL", "countdown.label")

        coords = self.layout.coords("countdown.event")
        font = self.layout.font("countdown.event")
        segments = parse_segments(graphics, label, self.colors.graphics_color("countdown.event"))
        total_width = self.__draw_scrolling_segments(
            canvas, graphics, coords, font, self.colors.graphics_color("default.background"), segments
        )
        self._scroll_x -= 1
        if self._scroll_x + total_width < -10:
            self._scroll_x = canvas.width

        # scrolling is handled here, so the screen is timed by its configured seconds
        return None

    def __draw_centered(self, canvas, graphics, text, keypath):
        coords = self.layout.coords(keypath)
        font = self.layout.font(keypath)
        x = center_text_position(text, coords["x"], font["size"]["width"])
        graphics.DrawText(canvas, font["font"], x, coords["y"], self.colors.graphics_color(keypath), text)

    def __draw_scrolling_segments(self, canvas, graphics, coords, font, bg_color, segments):
        """Draw (text, Color) segments, scrolling if they don't fit. Returns the text's pixel width."""
        x, y, width = coords["x"], coords["y"], coords["width"]
        char_width = font["size"]["width"]
        full_text = "".join(text for text, _ in segments)
        total_width = char_width * len(full_text)

        if total_width <= width:
            draw_x = center_text_position(full_text, abs(width // 2) + x, char_width)
            for text, color in segments:
                graphics.DrawText(canvas, font["font"], draw_x, y, color, text)
                draw_x += len(text) * char_width
            return 0

        draw_x = self._scroll_x
        for text, color in segments:
            graphics.DrawText(canvas, font["font"], draw_x, y, color, text)
            draw_x += len(text) * char_width

        # mask the edges so the text clips cleanly
        top = y + 1
        bottom = top - font["size"]["height"]
        for i in range(char_width):
            graphics.DrawLine(canvas, x - i - 1, top, x - i - 1, bottom, bg_color)
            graphics.DrawLine(canvas, x + width + i, top, x + width + i, bottom, bg_color)

        return total_width


def load() -> api.PLUGIN_DEFINITION:
    return Config, CountdownData, Renderer
