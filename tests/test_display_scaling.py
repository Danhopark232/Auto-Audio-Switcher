import unittest

import customtkinter as ctk

import UIaudio


class DisplayScalingTests(unittest.TestCase):
    CASES = (
        ("1366x768 at 100%", 1.00, 1366, 728),
        ("1920x1080 at 100%", 1.00, 1920, 1040),
        ("1920x1080 at 150%", 1.50, 1920, 1040),
        ("2560x1440 at 150%", 1.50, 2560, 1400),
        ("3840x2160 at 100%", 1.00, 3840, 2080),
        ("3840x2160 at 125%", 1.25, 3840, 2080),
        ("3840x2160 at 150%", 1.50, 3840, 2080),
        ("3840x2160 at 200%", 2.00, 3840, 2080),
        ("3840x2160 at 250%", 2.50, 3840, 2080),
        ("3840x2160 at 300%", 3.00, 3840, 2080),
    )

    def test_scale_fits_settings_window_inside_work_area(self):
        for label, native_scale, work_width, work_height in self.CASES:
            with self.subTest(label=label):
                scale = UIaudio.calculate_effective_ui_scale(native_scale, work_width, work_height)
                width, height = UIaudio.calculate_scaled_window_size(
                    UIaudio.SETTINGS_DEFAULT_WIDTH,
                    UIaudio.SETTINGS_DEFAULT_HEIGHT,
                    scale,
                )
                self.assertLessEqual(width + UIaudio.DISPLAY_FIT_MARGIN_X, work_width)
                self.assertLessEqual(height + UIaudio.DISPLAY_FIT_MARGIN_Y, work_height)
                self.assertLessEqual(scale, native_scale)
                self.assertGreaterEqual(scale, UIaudio.MIN_EFFECTIVE_UI_SCALE)

    def test_4k_common_scales_are_not_shrunk_unnecessarily(self):
        for native_scale in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0):
            with self.subTest(native_scale=native_scale):
                scale = UIaudio.calculate_effective_ui_scale(native_scale, 3840, 2080)
                self.assertAlmostEqual(scale, native_scale)

    def test_scaled_geometry_is_centered_in_offset_monitor_work_area(self):
        work_area = (1920, 0, 5760, 2080)
        geometry = UIaudio.centered_scaled_geometry(1124, 655, 2.0, work_area)
        self.assertEqual(geometry, "1124x655+2716+385")

    def test_customtkinter_live_dpi_reflow_is_disabled(self):
        self.assertTrue(ctk.ScalingTracker.deactivate_automatic_dpi_awareness)


if __name__ == "__main__":
    unittest.main()
