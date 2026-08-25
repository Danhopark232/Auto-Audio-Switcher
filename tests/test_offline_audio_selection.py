import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pycaw.pycaw import AudioUtilities
from pycaw.utils import AudioDeviceState

import UIaudio


def make_app():
    app = object.__new__(UIaudio.AutoAudioApp)
    app.config_data = {
        "speaker_name": "Offline Speakers",
        "speaker_id": "speaker-id",
        "headset_name": "Active Headset",
        "headset_id": "headset-id",
    }
    app.device_cache_lock = threading.Lock()
    app.audio_device_names = ["Active Headset"]
    app.audio_device_ids = {"Offline Speakers": "speaker-id", "Active Headset": "headset-id"}
    app.audio_device_id_cache_dirty = False
    app.current_audio_mode_cache = "headset"
    app.last_audio_sync_time = 0
    app.last_device_cache_refresh_time = 0
    app.last_audio_switch_failure_reason = None
    app.last_audio_switch_failure_target = None
    app.offline_audio_mode = None
    app.offline_audio_target = None
    return app


class OfflineAudioSelectionTests(unittest.TestCase):
    def test_offline_target_is_retained_when_switch_tools_cannot_confirm_it(self):
        app = make_app()
        app.refresh_audio_device_cache_if_stale = lambda force=False: False
        app.set_audio_with_pycaw = lambda target, device_id=None: False

        self.assertTrue(app.set_audio("speaker"))
        self.assertEqual(app.offline_audio_mode, "speaker")
        self.assertEqual(app.offline_audio_target, "Offline Speakers")
        self.assertEqual(app.current_audio_mode_cache, "speaker")

    def test_physical_fallback_does_not_override_retained_offline_target(self):
        app = make_app()
        app.remember_offline_audio_selection("speaker", "Offline Speakers")
        app.refresh_audio_device_cache_if_stale = lambda force=False: False
        app.get_current_audio_mode = lambda: self.fail("physical output must not replace an offline selection")

        self.assertEqual(app.get_cached_current_audio_mode(force=True), "speaker")
        self.assertEqual(app.offline_audio_mode, "speaker")

    def test_reconnected_target_is_rechecked_against_the_physical_output(self):
        app = make_app()
        app.remember_offline_audio_selection("speaker", "Offline Speakers")
        app.audio_device_names.append("Offline Speakers")
        app.refresh_audio_device_cache_if_stale = lambda force=False: False
        app.get_current_audio_mode = lambda: "headset"

        self.assertEqual(app.get_cached_current_audio_mode(), "headset")
        self.assertIsNone(app.offline_audio_mode)
        self.assertIsNone(app.offline_audio_target)

    def test_unplugged_pycaw_endpoint_is_not_added_to_active_device_names(self):
        app = make_app()
        device = SimpleNamespace(
            id="speaker-id",
            FriendlyName="Offline Speakers",
            friendly_name="Offline Speakers",
            state=AudioDeviceState.Unplugged,
        )

        with (
            patch.object(UIaudio, "initialize_com_for_thread", return_value=None),
            patch.object(UIaudio, "uninitialize_com_for_thread"),
            patch.object(AudioUtilities, "GetAllDevices", return_value=[device]),
            patch.object(AudioUtilities, "GetEndpointDataFlow", return_value="eRender"),
            patch.object(AudioUtilities, "SetDefaultDevice", return_value=None),
        ):
            self.assertTrue(app.set_audio_with_pycaw("Offline Speakers"))

        self.assertNotIn("Offline Speakers", app.audio_device_names)
        self.assertEqual(app.audio_device_ids["Offline Speakers"], "speaker-id")


if __name__ == "__main__":
    unittest.main()
