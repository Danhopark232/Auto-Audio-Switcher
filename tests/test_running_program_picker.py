import os
import sys
import unittest

import UIaudio


class RunningProgramPickerTests(unittest.TestCase):
    def test_recent_sort_prefers_visible_window_z_order(self):
        programs = [
            {"name": "Old foreground app", "window_rank": 0, "create_time": 10},
            {"name": "New background process", "window_rank": None, "create_time": 999},
            {"name": "Second visible app", "window_rank": 2, "create_time": 500},
        ]

        ordered = sorted(programs, key=UIaudio.running_program_recent_sort_key, reverse=True)

        self.assertEqual(
            [item["name"] for item in ordered],
            ["Old foreground app", "Second visible app", "New background process"],
        )

    def test_recent_sort_falls_back_to_process_start_time(self):
        programs = [
            {"name": "Older", "window_rank": None, "create_time": 100},
            {"name": "Newer", "window_rank": None, "create_time": 200},
        ]

        ordered = sorted(programs, key=UIaudio.running_program_recent_sort_key, reverse=True)

        self.assertEqual([item["name"] for item in ordered], ["Newer", "Older"])

    def test_visible_app_is_not_removed_by_resource_filter(self):
        self.assertTrue(UIaudio.should_include_running_program(0, 1, has_visible_window=True))
        self.assertFalse(UIaudio.should_include_running_program(0, 1, has_visible_window=False))

    @unittest.skipUnless(sys.platform == "win32", "Windows process query")
    def test_limited_process_query_recovers_current_executable_path(self):
        resolved = UIaudio.query_process_image_path(os.getpid())

        self.assertTrue(resolved)
        self.assertEqual(os.path.normcase(resolved), os.path.normcase(sys.executable))

    def test_program_icon_source_prefers_persisted_window_icon(self):
        app = object.__new__(UIaudio.AutoAudioApp)
        program = {
            "icon_path": r"C:\icons\captured.png",
            "path": r"C:\apps\example.exe",
        }

        self.assertEqual(app.get_program_icon_source(program), r"C:\icons\captured.png")


if __name__ == "__main__":
    unittest.main()
