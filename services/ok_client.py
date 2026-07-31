import logging
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yt_dlp

from utils.media import formatar_duracao

SEARCH_URL = "https://ok.ru/web-api/v2/video/fetchSearchResult"
BASE_DIR = Path(__file__).resolve().parent.parent
COOKIES_FILE = Path(os.environ.get("OKRU_COOKIES_FILE", str(BASE_DIR / "scraping" / "okru_cookies.json")))
COOKIE_DOMAINS = ("ok.ru", "okcdn.ru", "mycdn.me")


def _safe_cookie_value(value: Any) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _build_cookiefile_for_yt_dlp() -> Optional[str]:
    if not COOKIES_FILE.exists():
        return None
    try:
        raw = json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # pylint: disable=broad-except
        logging.warning("Falha lendo cookies para yt-dlp em %s: %s", COOKIES_FILE, exc)
        return None

    if not isinstance(raw, list):
        return None

    lines = ["# Netscape HTTP Cookie File\n"]
    loaded = 0
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        value = entry.get("value")
        domain = _safe_cookie_value(entry.get("domain") or "").strip()
        if not (name and value and domain):
            continue
        domain_lower = domain.lower()
        if not any(token in domain_lower for token in COOKIE_DOMAINS):
            continue

        include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"
        path = _safe_cookie_value(entry.get("path") or "/").strip() or "/"
        secure = "TRUE" if bool(entry.get("secure", False)) else "FALSE"

        expiry_raw = entry.get("expiry")
        try:
            expiry = int(expiry_raw) if expiry_raw is not None else 0
        except Exception:  # pylint: disable=broad-except
            expiry = 0

        lines.append(
            "\t".join(
                [
                    domain,
                    include_subdomains,
                    path,
                    secure,
                    str(expiry),
                    _safe_cookie_value(name),
                    _safe_cookie_value(value),
                ]
            )
            + "\n"
        )
        loaded += 1

    if loaded == 0:
        return None

    tmp = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".cookies.txt", delete=False)
    tmp.writelines(lines)
    tmp.close()
    return tmp.name


def buscar_videos(query: str, offset: int, duration: str = "", hd_quality: str = "") -> Dict[str, Any]:
    """
    Consulta a API do OK.ru para buscar vídeos ou canais.
    """
    payload = {
        "id": 25,
        "parameters": {
            "searchQuery": query,
            "currentStateId": "video",
            "durationType": duration or "ANY",
            "hd": hd_quality == "ON",
            "videosOffset": offset,
            "filters": {
                "st.cmd": "searchResult",
                "st.mode": "Movie",
                "st.gmode": "Groups",
                "st.query": query,
            },
        },
    }

    if duration:
        payload["parameters"]["filters"]["st.vln"] = duration

    logging.debug("OK.ru payload: %s", payload)
    response = requests.post(
        SEARCH_URL,
        json=payload,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
        },
    )

    logging.debug("OK.ru status=%s body=%s", response.status_code, response.text[:2000])
    if response.status_code != 200:
        return {"videos": [], "totalCount": 0}

    try:
        data = response.json()
    except Exception as exc:
        logging.warning("Erro parseando JSON OK.ru: %s", exc)
        return {"videos": [], "totalCount": 0}

    videos = _extrair_videos(data)
    if videos is not None:
        return videos

    canais = _extrair_canais(data)
    if canais is not None:
        return canais

    logging.info("Nenhum vídeo ou canal retornado para query '%s'", query)
    return {"videos": [], "totalCount": 0}


def _extract_video_info(video_id: str) -> Dict[str, Any]:
    video_url = f"https://ok.ru/video/{video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
    }

    cookiefile = _build_cookiefile_for_yt_dlp()
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    finally:
        if cookiefile:
            try:
                os.remove(cookiefile)
            except Exception:  # pylint: disable=broad-except
                pass
    if not info:
        raise RuntimeError("Nao foi possivel obter info do video.")
    return info


def _is_stream_manifest(fmt: Dict[str, Any]) -> bool:
    proto = (fmt.get("protocol") or "").lower()
    ext = (fmt.get("ext") or "").lower()
    return "m3u8" in proto or "dash" in proto or ext == "m3u8"


def _is_direct_video(fmt: Dict[str, Any]) -> bool:
    if not fmt.get("url") or _is_stream_manifest(fmt):
        return False
    ext = (fmt.get("ext") or "").lower()
    proto = (fmt.get("protocol") or "").lower()
    if "m3u8" in proto or "dash" in proto or ext not in {"mp4", "webm", "mov", "m4v"}:
        return False
    if (fmt.get("vcodec") or "").lower() == "none":
        return False
    # Não envia uma faixa sem áudio como se fosse um filme completo. Quando o
    # extractor não informa codecs, o formato continua elegível.
    if (fmt.get("acodec") or "").lower() == "none":
        return False
    return _effective_height(fmt) > 0


def _direct_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [fmt for fmt in (info.get("formats") or []) if _is_direct_video(fmt)]


def listar_resolucoes(video_id: str) -> Dict[str, Any]:
    """Returns the best direct, complete format available for each height."""
    info = _extract_video_info(video_id)
    by_height: Dict[int, Dict[str, Any]] = {}
    for fmt in _direct_formats(info):
        height = _effective_height(fmt)
        current = by_height.get(height)
        score = (fmt.get("tbr") or 0, fmt.get("filesize") or fmt.get("filesize_approx") or 0)
        current_score = (
            (current or {}).get("tbr") or 0,
            (current or {}).get("filesize") or (current or {}).get("filesize_approx") or 0,
        )
        if current is None or score > current_score:
            by_height[height] = fmt

    formats = []
    for height in sorted(by_height, reverse=True):
        fmt = by_height[height]
        formats.append(
            {
                "format_id": str(fmt.get("format_id") or ""),
                "height": height,
                "width": fmt.get("width"),
                "ext": fmt.get("ext") or "mp4",
                "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "fps": fmt.get("fps"),
            }
        )
    return {"title": info.get("title") or "", "formats": formats}


def extrair_link_download(
    video_id: str,
    prefer_height: Optional[int] = None,
    format_id: Optional[str] = None,
    include_http_headers: bool = False,
) -> Dict[str, Any]:
    """
    Usa yt_dlp para extrair um link direto (mp4/webm) do OK.ru sem baixar o arquivo.
    Se só houver manifestos HLS/DASH, retorna streaming=True para o front avisar.
    """
    info = _extract_video_info(video_id)

    formats = info.get("formats") or []
    diretos = _direct_formats(info)

    escolhido = None
    if format_id:
        escolhido = next((fmt for fmt in diretos if str(fmt.get("format_id") or "") == format_id), None)
        if escolhido is None:
            raise RuntimeError("A resolução selecionada não está mais disponível.")
    else:
        escolhido = _pick_direct(diretos, prefer_height)
    if escolhido:
        chosen_height = escolhido.get("height") or (_effective_height(escolhido) or None)
        result = {
            "url": escolhido["url"],
            "title": info.get("title", ""),
            "ext": escolhido.get("ext"),
            "streaming": False,
            "height": chosen_height,
        }
        if include_http_headers:
            headers = {}
            headers.update(info.get("http_headers") or {})
            headers.update(escolhido.get("http_headers") or {})
            result["http_headers"] = {
                key: value
                for key, value in headers.items()
                if key.lower() in {"user-agent", "accept", "accept-language", "sec-fetch-mode"}
            }
        return result

    manifestos = [f for f in formats if f.get("url") and _is_stream_manifest(f)]
    manifestos = sorted(manifestos, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
    if manifestos:
        escolhido = manifestos[0]
        return {
            "url": escolhido["url"],
            "title": info.get("title", ""),
            "ext": escolhido.get("ext"),
            "streaming": True,
            "height": escolhido.get("height"),
        }

    url = info.get("url")
    if url:
        return {"url": url, "title": info.get("title", ""), "streaming": True}

    raise RuntimeError("Nao foi possivel encontrar URL de download.")


def _effective_height(fmt: Dict[str, Any]) -> int:
    height = fmt.get("height")
    if isinstance(height, (int, float)) and height > 0:
        return int(height)

    fid = str(fmt.get("format_id") or "").lower()
    if "2160" in fid or "4k" in fid:
        return 2160
    if "1440" in fid or "2k" in fid:
        return 1440
    if "1080" in fid or "full" in fid:
        return 1080
    if "720" in fid or "hd" in fid or "high" in fid:
        return 720
    if "480" in fid or "sd" in fid or "medium" in fid:
        return 480
    if "360" in fid:
        return 360
    if "240" in fid or "lowest" in fid:
        return 240
    if "144" in fid or "mobile" in fid:
        return 144
    if "low" in fid:
        return 360
    return 0


def _pick_direct(fmts: List[dict], target_height: Optional[int] = None) -> Optional[dict]:
    if not fmts:
        return None

    def score(fmt: Dict[str, Any]):
        return (_effective_height(fmt), fmt.get("tbr") or 0)

    if target_height:
        abaixo = [f for f in fmts if _effective_height(f) <= target_height]
        abaixo = sorted(abaixo, key=score, reverse=True)
        if abaixo:
            return abaixo[0]
        acima = sorted(fmts, key=score)
        return acima[0]
    return sorted(fmts, key=score, reverse=True)[0]


def _extrair_videos(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    video_list = data.get("result", {}).get("videos", {}).get("list", [])
    total_count = data.get("result", {}).get("videos", {}).get("totalCount", 0)
    if not video_list:
        return None

    resultado: List[Dict[str, Any]] = []
    logging.info("Encontrado %s videos", len(video_list))
    for video in video_list:
        movie = video.get("movie", {})
        duracao_ms = movie.get("duration", 0)
        resultado.append(
            {
                "id": movie.get("id", ""),
                "title": movie.get("title", "Sem titulo"),
                "thumbnail": movie.get("thumbnail", {}).get("big", ""),
                "views": video.get("viewsCount", 0),
                "likes": movie.get("likesCount", 0),
                "duration": formatar_duracao(duracao_ms),
            }
        )
    return {"videos": resultado, "totalCount": total_count}


def _extrair_canais(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    channel_list = data.get("result", {}).get("channels", {}).get("list", [])
    total_count = data.get("result", {}).get("channels", {}).get("totalCount", 0)
    if not channel_list:
        return None

    resultado: List[Dict[str, Any]] = []
    logging.info("Encontrado %s canais/album", len(channel_list))
    for channel in channel_list:
        album = channel.get("album", {})
        resultado.append(
            {
                "id": album.get("id", ""),
                "title": album.get("name", "Sem titulo"),
                "thumbnail": album.get("imageUrl", ""),
                "views": album.get("views", 0),
                "likes": 0,
                "duration": f"{album.get('videoCount', 0)} videos",
            }
        )
    return {"videos": resultado, "totalCount": total_count}
