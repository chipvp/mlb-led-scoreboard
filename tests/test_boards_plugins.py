import json
import unittest
from datetime import date, datetime
from importlib.metadata import entry_points
from types import SimpleNamespace
from unittest import mock

from bullpen import PLUGIN_GROUP
from data.config.color import Color
from data.config.layout import Layout
from mlb_led_scoreboard_boards import clock, countdown

TODAY = date(2026, 6, 15)


def base_config(plugin_config, time_format="%-I"):
    return SimpleNamespace(
        scrolling_speed=0.1,
        time_format=time_format,
        plugin_config=plugin_config,
        parse_today=lambda: datetime(2026, 6, 15, 12, 0),
        is_postseason=lambda: False,
    )


def plugin_layout_and_colors(name):
    with open("coordinates/w64h32.example.json") as f:
        layout = Layout(json.load(f), 64, 32)
    with open("colors/scoreboard.example.json") as f:
        colors = Color(json.load(f))
    return layout.for_plugin(name), colors.for_plugin(name)


def fake_graphics():
    gfx = mock.MagicMock()
    gfx.Color.side_effect = lambda r, g, b: (r, g, b)
    return gfx


def fake_canvas():
    canvas = mock.MagicMock()
    canvas.width = 64
    return canvas


def drawn_text(gfx):
    return [call.args[5] for call in gfx.DrawText.call_args_list]


class TestEntryPoints(unittest.TestCase):
    def test_plugins_are_discoverable(self):
        names = {e.name for e in entry_points(group=PLUGIN_GROUP)}
        self.assertTrue({"clock", "countdown"} <= names)


class TestResolveDate(unittest.TestCase):
    def test_annual_date_later_this_year(self):
        self.assertEqual(countdown.resolve_date("12-25", TODAY), date(2026, 12, 25))

    def test_annual_date_rolls_to_next_year_once_passed(self):
        self.assertEqual(countdown.resolve_date("03-01", TODAY), date(2027, 3, 1))

    def test_today_is_not_rolled_over(self):
        self.assertEqual(countdown.resolve_date("06-15", TODAY), TODAY)

    def test_two_digit_year(self):
        self.assertEqual(countdown.resolve_date("07-04-27", TODAY), date(2027, 7, 4))

    def test_iso_date(self):
        self.assertEqual(countdown.resolve_date("2026-09-01", TODAY), date(2026, 9, 1))


class TestParseSegments(unittest.TestCase):
    def test_named_hex_and_close_tags(self):
        gfx = fake_graphics()
        default = "default"
        segments = countdown.parse_segments(gfx, "[red]Milo's[/] [#0000ff]Bday[/]", default)
        self.assertEqual(
            segments,
            [("Milo's", (220, 50, 50)), (" ", default), ("Bday", (0, 0, 255))],
        )

    def test_plain_label(self):
        self.assertEqual(countdown.parse_segments(fake_graphics(), "Opening Day", "d"), [("Opening Day", "d")])

    def test_empty_label(self):
        self.assertEqual(countdown.parse_segments(fake_graphics(), "", "d"), [("", "d")])


class TestCountdownData(unittest.TestCase):
    def active(self, events):
        config = countdown.Config(base_config({"events": events}))
        return countdown.CountdownData(config).active

    def test_sorted_by_days_remaining_and_past_events_dropped(self):
        events = [
            {"label": "Later", "date": "12-25"},
            {"label": "Soon", "date": "06-20"},
            {"label": "Past", "date": "2026-01-01"},
            {"label": "Today", "date": "06-15"},
        ]
        self.assertEqual(self.active(events), [("Today", 0), ("Soon", 5), ("Later", 193)])

    def test_invalid_events_are_skipped(self):
        events = [{"label": "No date"}, {"label": "Bad", "date": "not-a-date"}, {"label": "Ok", "date": "06-16"}]
        self.assertEqual(self.active(events), [("Ok", 1)])

    def test_no_events(self):
        self.assertEqual(self.active([]), [])


class TestCountdownRenderer(unittest.TestCase):
    def make(self, events, item_duration=10):
        layout, colors = plugin_layout_and_colors("countdown")
        config = countdown.Config(base_config({"events": events, "item_duration": item_duration}))
        return countdown.Renderer(config, layout, colors), countdown.CountdownData(config)

    def test_cannot_render_without_events(self):
        renderer, data = self.make([])
        self.assertFalse(renderer.can_render(data))

    def test_draws_days_and_label(self):
        renderer, data = self.make([{"label": "Opening Day", "date": "06-20"}])
        gfx = fake_graphics()
        renderer.render(data, fake_canvas(), gfx, 0)
        text = drawn_text(gfx)
        self.assertIn("5", text)
        self.assertIn("DAYS UNTIL", text)
        self.assertIn("Opening Day", text)

    def test_today_banner(self):
        renderer, data = self.make([{"label": "Game", "date": "06-15"}])
        gfx = fake_graphics()
        renderer.render(data, fake_canvas(), gfx, 0)
        self.assertIn("TODAY!", drawn_text(gfx))

    def test_rotates_to_next_event_after_item_duration(self):
        events = [{"label": "A", "date": "06-16"}, {"label": "B", "date": "06-17"}]
        renderer, data = self.make(events, item_duration=10)
        with mock.patch.object(countdown.time, "monotonic", side_effect=[100.0, 105.0, 111.0]):
            seen = []
            for _ in range(3):
                gfx = fake_graphics()
                renderer.render(data, fake_canvas(), gfx, 0)
                seen.append([t for t in drawn_text(gfx) if t in ("A", "B")])
        self.assertEqual(seen, [["A"], ["A"], ["B"]])

    def test_reset_restarts_from_first_event(self):
        events = [{"label": "A", "date": "06-16"}, {"label": "B", "date": "06-17"}]
        renderer, data = self.make(events, item_duration=1)
        with mock.patch.object(countdown.time, "monotonic", side_effect=[0.0, 5.0]):
            renderer.render(data, fake_canvas(), fake_graphics(), 0)
            renderer.render(data, fake_canvas(), fake_graphics(), 0)
        renderer.reset()
        gfx = fake_graphics()
        renderer.render(data, fake_canvas(), gfx, 0)
        self.assertIn("A", drawn_text(gfx))

    def test_long_label_scrolls(self):
        renderer, data = self.make([{"label": "A very long event label that cannot fit", "date": "06-20"}])
        gfx = fake_graphics()
        renderer.render(data, fake_canvas(), gfx, 0)
        self.assertTrue(gfx.DrawLine.called)


class TestClock(unittest.TestCase):
    def render(self, time_format):
        layout, colors = plugin_layout_and_colors("clock")
        config = clock.Config(base_config({}, time_format=time_format))
        gfx = fake_graphics()
        renderer = clock.Renderer(config, layout, colors)
        result = renderer.render(clock.ClockData(config), fake_canvas(), gfx, 0)
        return result, drawn_text(gfx)

    def test_draws_time_and_date(self):
        with mock.patch.object(clock.time, "strftime", side_effect=lambda fmt: fmt):
            result, text = self.render("%-I")
        self.assertIsNone(result)
        self.assertEqual(text, ["%-I:%M%p", "%a %b %-d"])

    def test_24h_has_no_am_pm(self):
        with mock.patch.object(clock.time, "strftime", side_effect=lambda fmt: fmt):
            _, text = self.render("%H")
        self.assertEqual(text[0], "%H:%M")


if __name__ == "__main__":
    unittest.main()


class TestLoadedThroughPluginLoader(unittest.TestCase):
    def test_screens_in_rotation_load_both_plugins(self):
        import tempfile
        from pathlib import Path

        from data.plugins import load_plugins
        from tests.helpers import TEST_CONFIG_PATH, make_test_config

        with open(TEST_CONFIG_PATH) as f:
            raw = json.load(f)
        raw["rotation"]["screens"] += [
            {"kind": "clock", "seconds": 10, "with_priority": 0},
            {"kind": "countdown", "seconds": 20, "with_priority": 0},
        ]
        raw["plugins"] = {"countdown": {"events": [{"label": "Test", "date": "12-25"}]}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(raw))
            config = make_test_config(config=str(path.with_suffix("")), led_cols=64, led_rows=32)

        plugins = load_plugins(config)
        self.assertTrue({"clock", "countdown"} <= set(plugins))
        data, renderer = plugins["countdown"]
        self.assertEqual(len(data.active), 1)
        self.assertTrue(renderer.can_render(data))
