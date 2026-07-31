import os
import unittest
from unittest.mock import MagicMock, patch

from services import jdownloader_client


class JDownloaderClientTest(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(
            os.environ,
            {
                "MYJD_EMAIL": "admin@example.test",
                "MYJD_PASSWORD": "secret",
                "MYJD_DEVICE": "test-device",
                "MYJD_DOWNLOAD_FOLDER": "/output",
            },
        )
        self.env_patch.start()
        jdownloader_client._cached_client = None  # pylint: disable=protected-access
        jdownloader_client._cached_device = None  # pylint: disable=protected-access
        jdownloader_client._cached_config = None  # pylint: disable=protected-access
        jdownloader_client._configured_rule_key = None  # pylint: disable=protected-access

    def tearDown(self):
        self.env_patch.stop()

    def test_adds_and_autostarts_in_container_output_folder(self):
        device = MagicMock()
        device.linkgrabber.add_links.return_value = {"id": 42}
        device.linkgrabber.query_links.return_value = [
            {"uuid": 100, "packageUUID": 200, "availability": "ONLINE"}
        ]
        device.config.get.return_value = []
        client = MagicMock()
        client.get_device.return_value = device

        with patch.object(jdownloader_client.myjdapi, "Myjdapi", return_value=client):
            result = jdownloader_client.add_download(
                "https://cdn.example/movie.mp4",
                "Meu Filme",
                "https://ok.ru/video/123",
                {"User-Agent": "Browser UA"},
                "Meu Filme.mp4",
            )

        self.assertEqual(result, {"job_id": 42, "links": 1, "verified": True})
        client.connect.assert_called_once_with("admin@example.test", "secret")
        client.get_device.assert_called_once_with(device_name="test-device")
        device.disable_direct_connection.assert_called_once_with()
        payload = device.linkgrabber.add_links.call_args.args[0][0]
        self.assertEqual(payload["destinationFolder"], "/output")
        self.assertEqual(payload["packageName"], "Meu Filme")
        self.assertFalse(payload["autostart"])
        self.assertTrue(payload["assignJobID"])
        device.linkgrabber.rename_link.assert_called_once_with(100, "Meu Filme.mp4")
        device.linkgrabber.move_to_downloadlist.assert_called_once_with([100], [200])
        device.downloads.force_download.assert_called_once_with([100], [200])
        rules = device.config.set.call_args_list[0].args[3]
        self.assertEqual(rules[-1]["pattern"], "https://[^/]+[.]okcdn[.]ru/.+")


if __name__ == "__main__":
    unittest.main()
