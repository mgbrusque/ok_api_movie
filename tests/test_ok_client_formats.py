import unittest
from unittest.mock import patch

from services import ok_client


class OkClientFormatsTest(unittest.TestCase):
    def setUp(self):
        self.info = {
            "title": "Filme",
            "http_headers": {"User-Agent": "Browser UA", "X-Ignore": "secret"},
            "formats": [
                {
                    "format_id": "sd-low",
                    "url": "https://cdn/sd-low.mp4",
                    "ext": "mp4",
                    "height": 480,
                    "tbr": 500,
                    "vcodec": "h264",
                    "acodec": "aac",
                },
                {
                    "format_id": "sd-best",
                    "url": "https://cdn/sd-best.mp4",
                    "ext": "mp4",
                    "height": 480,
                    "tbr": 900,
                    "filesize": 1000,
                    "vcodec": "h264",
                    "acodec": "aac",
                },
                {
                    "format_id": "hd",
                    "url": "https://cdn/hd.mp4",
                    "ext": "mp4",
                    "height": 720,
                    "tbr": 1200,
                    "vcodec": "h264",
                    "acodec": "aac",
                },
                {
                    "format_id": "silent",
                    "url": "https://cdn/silent.mp4",
                    "ext": "mp4",
                    "height": 1080,
                    "vcodec": "h264",
                    "acodec": "none",
                },
                {
                    "format_id": "hls",
                    "url": "https://cdn/master.m3u8",
                    "ext": "mp4",
                    "protocol": "m3u8_native",
                    "height": 1080,
                    "vcodec": "h264",
                    "acodec": "aac",
                },
            ],
        }

    def test_lists_one_complete_direct_format_per_height(self):
        with patch.object(ok_client, "_extract_video_info", return_value=self.info):
            result = ok_client.listar_resolucoes("123")

        self.assertEqual(result["title"], "Filme")
        self.assertEqual(
            [(item["height"], item["format_id"]) for item in result["formats"]],
            [(720, "hd"), (480, "sd-best")],
        )

    def test_extracts_the_exact_selected_format(self):
        with patch.object(ok_client, "_extract_video_info", return_value=self.info):
            result = ok_client.extrair_link_download(
                "123", format_id="sd-best", include_http_headers=True
            )
        self.assertEqual(result["url"], "https://cdn/sd-best.mp4")
        self.assertEqual(result["height"], 480)
        self.assertEqual(result["http_headers"], {"User-Agent": "Browser UA"})

    def test_rejects_a_stale_or_forged_format(self):
        with patch.object(ok_client, "_extract_video_info", return_value=self.info):
            with self.assertRaisesRegex(RuntimeError, "não está mais disponível"):
                ok_client.extrair_link_download("123", format_id="forged")


if __name__ == "__main__":
    unittest.main()
