import os
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as app_module
from services import auth


class AuthAndAdminRoutesTest(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(
            os.environ,
            {
                "APP_ADMIN_USERNAME": "admin",
                "APP_ADMIN_PASSWORD_HASH": generate_password_hash("senha-de-teste"),
            },
        )
        self.env_patch.start()
        auth._login_attempts.clear()  # pylint: disable=protected-access
        app_module.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        self.client = app_module.app.test_client()

    def tearDown(self):
        self.env_patch.stop()

    def _csrf(self):
        response = self.client.get("/auth/status")
        self.assertEqual(response.status_code, 200)
        return response.get_json()["csrf_token"]

    def _login(self):
        token = self._csrf()
        response = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "senha-de-teste"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(response.status_code, 200)
        return response.get_json()["csrf_token"]

    def test_login_requires_csrf_and_valid_credentials(self):
        response = self.client.post(
            "/auth/login", json={"username": "admin", "password": "senha-de-teste"}
        )
        self.assertEqual(response.status_code, 403)

        token = self._csrf()
        response = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "errada"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "senha-de-teste"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["authenticated"])

    def test_login_is_blocked_after_too_many_failures(self):
        token = self._csrf()
        for _ in range(auth.login_max_attempts()):
            response = self.client.post(
                "/auth/login",
                json={"username": "admin", "password": "errada"},
                headers={"X-CSRF-Token": token},
            )
            self.assertEqual(response.status_code, 401)

        response = self.client.post(
            "/auth/login",
            json={"username": "admin", "password": "ainda-errada"},
            headers={"X-CSRF-Token": token},
        )
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers["Retry-After"]), 0)
        self.assertEqual(response.get_json()["code"], "too_many_attempts")

    def test_formats_are_private(self):
        response = self.client.get("/admin/formats/123")
        self.assertEqual(response.status_code, 401)

        self._login()
        expected = {"title": "Filme", "formats": [{"format_id": "hd", "height": 720}]}
        with patch.object(app_module, "listar_resolucoes", return_value=expected):
            response = self.client.get("/admin/formats/123")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), expected)

    def test_selected_format_is_sent_to_jdownloader(self):
        token = self._login()
        extracted = {
            "url": "https://cdn.example/video.mp4?token=short-lived",
            "title": "Título",
            "ext": "mp4",
            "height": 1080,
            "streaming": False,
            "http_headers": {"User-Agent": "Browser UA"},
        }
        with (
            patch.object(app_module, "extrair_link_download", return_value=extracted) as extract,
            patch.object(app_module, "add_download", return_value={"id": 10}) as add,
        ):
            response = self.client.post(
                "/admin/jdownloader",
                json={"video_id": "123", "format_id": "full", "title": "Filme: Teste"},
                headers={"X-CSRF-Token": token},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["queued"])
        extract.assert_called_once_with("123", format_id="full", include_http_headers=True)
        add.assert_called_once_with(
            extracted["url"],
            "Filme Teste",
            source_url="https://ok.ru/video/123",
            http_headers={"User-Agent": "Browser UA"},
            filename="Filme Teste.mp4",
        )

    def test_jdownloader_post_requires_csrf(self):
        self._login()
        response = self.client.post(
            "/admin/jdownloader",
            json={"video_id": "123", "format_id": "hd", "title": "Filme"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
