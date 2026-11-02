import tempfile
import unittest
from pathlib import Path
from unittest import mock

import brightness_manager as bm


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


class StartupLogoTest(unittest.TestCase):
    def test_logo_skipped_while_panel_is_off(self):
        import main

        self.assertTrue(main.should_draw_startup_logo(True, True, False))
        self.assertFalse(main.should_draw_startup_logo(True, True, True))
        self.assertFalse(main.should_draw_startup_logo(False, True, False))
        self.assertFalse(main.should_draw_startup_logo(True, False, False))


class FakeMatrix:
    def __init__(self):
        self.brightness = None
        self.cleared = 0

    def Clear(self):
        self.cleared += 1


class TestBrightnessManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.shared = Path(self.tmp.name) / "state"
        self.local = Path(self.tmp.name) / "local"
        self.clock = FakeClock()
        for patch in (
            mock.patch.dict("os.environ", {"MLB_PANEL_STATE": str(self.shared)}),
            mock.patch.object(bm, "FALLBACK_STATE_FILE", self.local),
            mock.patch.object(bm, "_clock", self.clock),
            mock.patch("builtins.print"),
        ):
            patch.start()
            self.addCleanup(patch.stop)
        bm.reset()
        self.addCleanup(bm.reset)
        self.matrix = FakeMatrix()

    def tick(self, seconds=1.5):
        self.clock.now += seconds

    def test_defaults_with_no_files(self):
        bm.register_matrix(self.matrix)
        self.assertEqual((bm.get_brightness(), bm.is_off()), (100, False))
        self.assertEqual(self.matrix.brightness, 100)

    def test_reads_shared_file_and_applies_to_matrix(self):
        self.shared.write_text("40,on\n")
        bm.register_matrix(self.matrix)
        self.assertEqual((bm.get_brightness(), bm.is_off()), (40, False))
        self.assertEqual(self.matrix.brightness, 40)

    def test_clamps_brightness(self):
        for text, expected in (("0,on", 1), ("-5,on", 1), ("250,on", 100)):
            with self.subTest(text=text):
                bm.reset()
                self.shared.write_text(text)
                self.assertEqual(bm.get_brightness(), expected)

    def test_off_keeps_brightness_and_clears_once(self):
        self.shared.write_text("40,on")
        bm.register_matrix(self.matrix)
        self.shared.write_text("40,off")
        self.tick()
        self.assertTrue(bm.is_off())
        self.assertEqual(bm.get_brightness(), 40)
        self.assertEqual(self.matrix.cleared, 1)
        self.tick()
        self.assertTrue(bm.is_off())
        self.assertEqual(self.matrix.cleared, 1)

    def test_turning_back_on_applies_brightness(self):
        self.shared.write_text("40,off")
        bm.register_matrix(self.matrix)
        self.shared.write_text("55,on")
        self.tick()
        self.assertFalse(bm.is_off())
        self.assertEqual(self.matrix.brightness, 55)

    def test_garbage_empty_or_unreadable_keeps_last_good(self):
        self.shared.write_text("40,off")
        self.assertTrue(bm.is_off())
        for bad in (b"", b"banana", b"40", b"40,maybe", b"x,on", b"\xff\xfe\x00"):
            with self.subTest(bad=bad):
                self.shared.write_bytes(bad)
                self.tick()
                self.assertEqual((bm.get_brightness(), bm.is_off()), (40, True))

    def test_no_flash_to_100_on_transient_empty_read(self):
        self.shared.write_text("20,on")
        bm.register_matrix(self.matrix)
        self.shared.write_text("")
        self.tick()
        self.assertEqual(bm.get_brightness(), 20)
        self.assertEqual(self.matrix.brightness, 20)

    def test_garbage_before_any_good_read_uses_default(self):
        self.shared.write_text("junk")
        self.assertEqual((bm.get_brightness(), bm.is_off()), (100, False))

    def test_unreadable_shared_path_keeps_last_good(self):
        self.shared.write_text("30,on")
        self.assertEqual(bm.get_brightness(), 30)
        self.shared.unlink()
        self.shared.mkdir()
        self.tick()
        self.assertEqual(bm.get_brightness(), 30)

    def test_bom_is_tolerated(self):
        self.shared.write_bytes(b"\xef\xbb\xbf35,off")
        self.assertEqual((bm.get_brightness(), bm.is_off()), (35, True))

    def test_local_fallback_only_when_shared_is_missing(self):
        self.local.write_text("60,on")
        self.assertEqual(bm.get_brightness(), 60)
        self.shared.write_text("junk")  # present but garbage: must not use the local file
        self.local.write_text("90,on")
        self.tick()
        self.assertEqual(bm.get_brightness(), 60)
        self.shared.write_text("25,on")
        self.tick()
        self.assertEqual(bm.get_brightness(), 25)

    def test_vanished_shared_file_keeps_shared_value_not_stale_local(self):
        self.shared.write_text("55,on")
        self.assertEqual(bm.get_brightness(), 55)
        self.local.write_text("40,off")
        self.shared.unlink()
        self.tick()
        self.assertEqual((bm.get_brightness(), bm.is_off()), (55, False))

    def test_unreadable_shared_never_uses_stale_local(self):
        self.local.write_text("40,off")
        self.shared.mkdir()  # IsADirectoryError, not FileNotFoundError
        self.assertEqual((bm.get_brightness(), bm.is_off()), (100, False))
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("denied")):
            self.tick()
            self.assertEqual((bm.get_brightness(), bm.is_off()), (100, False))

    def test_poll_is_throttled_to_once_a_second(self):
        self.shared.write_text("40,on")
        self.assertEqual(bm.get_brightness(), 40)
        self.shared.write_text("70,on")
        self.tick(0.5)
        self.assertEqual(bm.get_brightness(), 40)
        self.tick(0.6)
        self.assertEqual(bm.get_brightness(), 70)

    def test_matrix_errors_do_not_propagate(self):
        class Broken(FakeMatrix):
            def Clear(self):
                raise RuntimeError("boom")

        self.shared.write_text("40,off")
        bm.register_matrix(Broken())
        self.assertTrue(bm.is_off())
