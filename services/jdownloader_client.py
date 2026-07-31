import os
import threading
import time
from dataclasses import dataclass

import myjdapi


class JDownloaderConfigurationError(RuntimeError):
    """Raised when the MyJDownloader integration is not configured."""


class JDownloaderError(RuntimeError):
    """Raised when MyJDownloader rejects or cannot complete a request."""


@dataclass(frozen=True)
class JDownloaderSettings:
    email: str
    password: str
    device: str
    download_folder: str


def get_settings() -> JDownloaderSettings:
    settings = JDownloaderSettings(
        email=(os.environ.get("MYJD_EMAIL") or "").strip(),
        password=os.environ.get("MYJD_PASSWORD") or "",
        device=(os.environ.get("MYJD_DEVICE") or "").strip(),
        download_folder=(os.environ.get("MYJD_DOWNLOAD_FOLDER") or "/output").strip(),
    )
    missing = [
        name
        for name, value in (
            ("MYJD_EMAIL", settings.email),
            ("MYJD_PASSWORD", settings.password),
            ("MYJD_DEVICE", settings.device),
            ("MYJD_DOWNLOAD_FOLDER", settings.download_folder),
        )
        if not value
    ]
    if missing:
        raise JDownloaderConfigurationError(
            "Configuração do MyJDownloader incompleta: " + ", ".join(missing)
        )
    return settings


_client_lock = threading.Lock()
_cached_config: tuple[str, str, str] | None = None
_cached_client = None
_cached_device = None
_configured_rule_key: tuple[str, str] | None = None

OKCDN_RULE_NAME = "Cooframe OK CDN"
LINKCRAWLER_CONFIG_INTERFACE = "jd.controlling.linkcrawler.LinkCrawlerConfig"
OKCDN_PATTERN = "https://[^/]+[.]okcdn[.]ru/.+"


def _connect(settings: JDownloaderSettings):
    global _cached_client, _cached_config, _cached_device
    cache_key = (settings.email, settings.password, settings.device)
    if _cached_device is not None and _cached_config == cache_key:
        return _cached_device

    client = myjdapi.Myjdapi()
    client.connect(settings.email, settings.password)
    device = client.get_device(device_name=settings.device)
    # A API em nuvem funciona em qualquer hospedagem. Evita tentativas lentas nos
    # endereços LAN/WAN anunciados pela porta de conexão direta 3129.
    device.disable_direct_connection()
    _cached_client = client
    _cached_device = device
    _cached_config = cache_key
    return device


def _ensure_okcdn_directhttp_rule(device, settings: JDownloaderSettings, http_headers: dict) -> None:
    global _configured_rule_key
    user_agent = str(http_headers.get("User-Agent") or "").strip()
    if not user_agent:
        raise JDownloaderError("O extractor não forneceu o User-Agent necessário para o OK.ru.")

    rule_key = (settings.device, user_agent)
    if _configured_rule_key == rule_key:
        return

    rules = device.config.get(
        LINKCRAWLER_CONFIG_INTERFACE,
        "null",
        "LinkCrawlerRules",
    ) or []
    expected_rule = {
        "enabled": True,
        "logging": False,
        "maxDecryptDepth": 1,
        "name": OKCDN_RULE_NAME,
        "pattern": OKCDN_PATTERN,
        "rule": "DIRECTHTTP",
        "headers": [["User-Agent", user_agent]],
    }
    current = next((rule for rule in rules if rule.get("name") == OKCDN_RULE_NAME), None)
    comparable_keys = {"enabled", "logging", "maxDecryptDepth", "name", "pattern", "rule", "headers"}
    if current is None or any(current.get(key) != expected_rule.get(key) for key in comparable_keys):
        preserved = [rule for rule in rules if rule.get("name") != OKCDN_RULE_NAME]
        preserved.append(expected_rule)
        device.config.set(
            LINKCRAWLER_CONFIG_INTERFACE,
            "null",
            "LinkCrawlerRules",
            preserved,
        )
    device.config.set(
        LINKCRAWLER_CONFIG_INTERFACE,
        "null",
        "LinkCrawlerRulesEnabled",
        True,
    )
    _configured_rule_key = rule_key


def _wait_for_captured_links(device, job_id: int, timeout_seconds: int = 30) -> list[dict]:
    query = [
        {
            "jobUUIDs": [job_id],
            "name": True,
            "status": True,
            "availability": True,
            "host": True,
            "maxResults": 20,
            "startAt": 0,
        }
    ]
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        links = device.linkgrabber.query_links(query) or []
        if links:
            return links
        time.sleep(1)
    return []


def add_download(
    url: str,
    package_name: str,
    source_url: str | None = None,
    http_headers: dict | None = None,
    filename: str | None = None,
) -> dict:
    """Captures, verifies and starts a direct OK CDN URL on JDownloader."""
    global _cached_client, _cached_config, _cached_device, _configured_rule_key
    settings = get_settings()
    payload = {
        "autostart": False,
        "assignJobID": True,
        "links": url,
        "packageName": package_name,
        "destinationFolder": settings.download_folder,
        "overwritePackagizerRules": True,
        "priority": "DEFAULT",
    }
    if source_url:
        payload["sourceUrl"] = source_url

    with _client_lock:
        try:
            device = _connect(settings)
            _ensure_okcdn_directhttp_rule(device, settings, http_headers or {})
            result = device.linkgrabber.add_links([payload])
            job_id = (result or {}).get("id")
            if not job_id:
                raise JDownloaderError("O MyJDownloader não criou o trabalho de captura.")

            captured = _wait_for_captured_links(device, job_id)
            if not captured:
                raise JDownloaderError("O JDownloader não reconheceu o link dentro do tempo esperado.")

            link_ids = [item["uuid"] for item in captured if item.get("uuid")]
            package_ids = list({item["packageUUID"] for item in captured if item.get("packageUUID")})
            if not link_ids:
                raise JDownloaderError("O JDownloader não retornou um arquivo válido para download.")

            if filename:
                for link_id in link_ids:
                    device.linkgrabber.rename_link(link_id, filename)
            device.linkgrabber.move_to_downloadlist(link_ids, package_ids)
            device.downloads.force_download(link_ids, package_ids)
        except Exception as exc:  # pylint: disable=broad-except
            _cached_client = None
            _cached_device = None
            _cached_config = None
            _configured_rule_key = None
            if isinstance(exc, (JDownloaderError, JDownloaderConfigurationError)):
                raise
            raise JDownloaderError("Não foi possível comunicar com o MyJDownloader.") from exc

    return {"job_id": job_id, "links": len(link_ids), "verified": True}
