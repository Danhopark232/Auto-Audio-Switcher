import json
import os
import tempfile
import unittest

import UIaudio


class SecurityCompatibilityTests(unittest.TestCase):
    def test_frozen_app_uses_per_user_local_app_data(self):
        data_dir = UIaudio.get_app_data_dir(
            app_dir=r"C:\Program Files\AutoAudioSwitcher",
            frozen=True,
            local_app_data=r"C:\Users\Example\AppData\Local",
        )

        self.assertEqual(data_dir, r"C:\Users\Example\AppData\Local\AutoAudioSwitcher")

    def test_source_run_keeps_workspace_data_location(self):
        self.assertEqual(
            UIaudio.get_app_data_dir(app_dir=r"D:\Source", frozen=False, local_app_data=r"C:\Ignored"),
            r"D:\Source",
        )

    def test_legacy_config_migration_preserves_existing_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            legacy = os.path.join(temp_dir, "legacy", "config.json")
            destination = os.path.join(temp_dir, "data", "config.json")
            os.makedirs(os.path.dirname(legacy))
            with open(legacy, "w", encoding="utf-8") as file:
                json.dump({"source": "legacy"}, file)

            self.assertTrue(UIaudio.migrate_legacy_config(destination, legacy))
            self.assertFalse(UIaudio.migrate_legacy_config(destination, legacy))
            self.assertEqual(UIaudio.read_config_object(destination), {"source": "legacy"})

    def test_oversized_config_is_rejected_before_json_parsing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = os.path.join(temp_dir, "config.json")
            with open(path, "wb") as file:
                file.write(b"{} " * 10)

            with self.assertRaises(ValueError):
                UIaudio.read_config_object(path, max_bytes=8)

    def test_diagnostics_option_supports_separate_and_equals_syntax(self):
        self.assertEqual(
            UIaudio.command_line_option_value(["app", "--diagnostics-dir", r"C:\Temp\diag"], "--diagnostics-dir"),
            r"C:\Temp\diag",
        )

    def test_manifest_declares_windows_10_compatibility_and_standard_user_level(self):
        manifest_path = os.path.join(os.path.dirname(UIaudio.__file__), "app.manifest")
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = file.read()

        self.assertIn("8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a", manifest)
        self.assertIn('level="asInvoker"', manifest)
        self.assertIn('uiAccess="false"', manifest)
        self.assertEqual(
            UIaudio.command_line_option_value(["app", r"--diagnostics-dir=C:\Temp\diag"], "--diagnostics-dir"),
            r"C:\Temp\diag",
        )

    def test_distribution_uses_native_audio_backend_without_general_command_helper(self):
        project_dir = os.path.dirname(UIaudio.__file__)
        with open(os.path.join(project_dir, "AutoAudioSwitcher.spec"), "r", encoding="utf-8") as file:
            spec = file.read().lower()
        with open(
            os.path.join(project_dir, "installer", "Install_AutoAudioSwitcher.ps1"),
            "r",
            encoding="utf-8-sig",
        ) as file:
            installer = file.read().lower()

        self.assertNotIn("nircmd", spec)
        self.assertNotIn("nircmd", installer)
        self.assertIn(r"$env:localappdata\programs\autoaudioswitcher", installer)


if __name__ == "__main__":
    unittest.main()
