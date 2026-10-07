import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pyhap.loader import Loader

import brightness_manager
import homekit_server


def make_accessory(brightness, off):
    driver = mock.MagicMock()
    driver.loader = Loader()  # real services and characteristics, no network or event loop
    with mock.patch.object(brightness_manager, "get_brightness", return_value=brightness):
        with mock.patch.object(brightness_manager, "is_off", return_value=off):
            return homekit_server.BrightnessAccessory(driver, "Brightness")


class TestAccessoryStartsFromSavedState(unittest.TestCase):
    def test_board_on_shows_on_at_saved_brightness(self):
        accessory = make_accessory(brightness=56, off=False)
        self.assertTrue(accessory.char_on.value)
        self.assertEqual(accessory.char_brightness.value, 56)

    def test_board_off_shows_off_but_remembers_brightness(self):
        accessory = make_accessory(brightness=40, off=True)
        self.assertFalse(accessory.char_on.value)
        self.assertEqual(accessory.char_brightness.value, 40)

    def test_turning_on_restores_saved_brightness_not_100(self):
        accessory = make_accessory(brightness=40, off=True)
        with mock.patch.object(brightness_manager, "power_on") as power_on:
            accessory.set_on(True)
        power_on.assert_called_once_with(40)

    def test_setting_brightness_updates_what_power_on_restores(self):
        accessory = make_accessory(brightness=40, off=False)
        with mock.patch.object(brightness_manager, "set_brightness"):
            accessory.set_brightness(75)
        with mock.patch.object(brightness_manager, "power_on") as power_on:
            accessory.set_on(True)
        power_on.assert_called_once_with(75)


class TestBrightnessManagerPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state_file = Path(self.tmp.name) / "state"
        for patch in (
            mock.patch.object(brightness_manager, "_STATE_FILE", self.state_file),
            mock.patch.object(brightness_manager, "_brightness", 100),
            mock.patch.object(brightness_manager, "_is_off", True),
            mock.patch.object(brightness_manager, "_matrix_ref", None),
            mock.patch("builtins.print"),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def test_power_on_saves_the_level_it_was_given(self):
        brightness_manager.power_on(70)
        self.assertEqual(brightness_manager.get_brightness(), 70)
        self.assertFalse(brightness_manager.is_off())
        self.assertEqual(self.state_file.read_text(), "70,on")

    def test_state_round_trips_through_the_file(self):
        brightness_manager.set_brightness(33)
        brightness_manager.power_off()
        self.assertEqual(brightness_manager._load_state(), (33, True))


if __name__ == "__main__":
    unittest.main()
