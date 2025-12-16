import logging
from typing import Any, Dict, List, Optional

import requests
import yt_dlp

from utils.media import formatar_duracao

SEARCH_URL = "https://ok.ru/web-api/v2/video/fetchSearchResult"


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


def extrair_link_download(video_id: str, prefer_height: Optional[int] = None) -> Dict[str, Any]:
    """
    Usa yt_dlp para extrair um link direto (mp4/webm) do OK.ru sem baixar o arquivo.
    Se só houver manifestos HLS/DASH, retorna streaming=True para o front avisar.
    """
    video_url = f"https://ok.ru/video/{video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
    if not info:
        raise RuntimeError("Nao foi possivel obter info do video.")

    formats = info.get("formats") or []

    def is_stream_manifest(fmt):
        proto = (fmt.get("protocol") or "").lower()
        ext = (fmt.get("ext") or "").lower()
        return "m3u8" in proto or "dash" in proto or ext == "m3u8"

    def is_direct(fmt):
        if not fmt.get("url") or is_stream_manifest(fmt):
            return False
        ext = (fmt.get("ext") or "").lower()
        proto = (fmt.get("protocol") or "").lower()
        if "m3u8" in proto or "dash" in proto:
            return False
        return ext in {"mp4", "webm", "mov", "m4v"}

    diretos = [f for f in formats if is_direct(f)]

    escolhido = _pick_direct(diretos, prefer_height)
    if escolhido:
        return {
            "url": escolhido["url"],
            "title": info.get("title", ""),
            "ext": escolhido.get("ext"),
            "streaming": False,
            "height": escolhido.get("height"),
        }

    manifestos = [f for f in formats if f.get("url") and is_stream_manifest(f)]
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


def _pick_direct(fmts: List[dict], target_height: Optional[int] = None) -> Optional[dict]:
    if not fmts:
        return None
    if target_height:
        abaixo = [f for f in fmts if (f.get("height") or 0) <= target_height]
        abaixo = sorted(abaixo, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
        if abaixo:
            return abaixo[0]
        acima = sorted(fmts, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0))
        return acima[0]
    return sorted(fmts, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)[0]


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
