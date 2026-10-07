import time

import bullpen.api as api
from bullpen.time_formats import TIME_FORMAT_12H, os_datetime_format
from bullpen.util import center_text_position

DEFAULT_DATE_FORMAT = "%a %b %-d"


class Config(api.PluginConfig):
    def __init__(self, config: api.MLBConfig) -> None:
        self.time_format = config.time_format
        self.date_format = os_datetime_format(config.plugin_config.get("date_format", DEFAULT_DATE_FORMAT))


class ClockData(api.PluginData):
    def __init__(self, config: Config) -> None:
        self.config = config

    def update(self, force: bool = False) -> api.UpdateStatus:
        # the time comes from the system clock, there is nothing to fetch
        return api.UpdateStatus.DEFERRED


class Renderer(api.PluginRenderer[ClockData]):
    def __init__(self, config: Config, layout: api.Layout, colors: api.Color) -> None:
        self.layout = layout
        self.colors = colors

    def wait_time(self) -> float:
        return 1.0

    def render(self, data, canvas, graphics, scrolling_text_pos):
        config = data.config
        bgcolor = self.colors.color("default.background")
        canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])

        # e.g. "3:45PM"
        time_fmt = "{}:%M{}".format(config.time_format, "%p" if config.time_format == TIME_FORMAT_12H else "")
        self.__draw_centered(canvas, graphics, "clock.time", time.strftime(time_fmt))
        # e.g. "Mon Mar 31"
        self.__draw_centered(canvas, graphics, "clock.date", time.strftime(config.date_format))

        return None

    def __draw_centered(self, canvas, graphics, keypath, text):
        coords = self.layout.coords(keypath)
        font = self.layout.font(keypath)
        color = self.colors.graphics_color(keypath)
        x = center_text_position(text, coords["x"], font["size"]["width"])
        graphics.DrawText(canvas, font["font"], x, coords["y"], color, text)


def load() -> api.PLUGIN_DEFINITION:
    return Config, ClockData, Renderer
