import html
import os
from typing import Any, Dict, Optional, Tuple

import requests

from utils.title_cleaner import generate_candidates, score_tmdb_result

TMDB_API_KEY = os.environ.get("KEY_API_TMDB")
TMDB_BEARER_TOKEN = os.environ.get("TOKEN_API_TMDB")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"


def _tmdb_request(path: str, params: dict | None, lang: str | None):
    params = params or {}
    headers = {"Accept": "application/json"}
    if TMDB_API_KEY:
        params.setdefault("api_key", TMDB_API_KEY)
    if TMDB_BEARER_TOKEN:
        headers["Authorization"] = f"Bearer {TMDB_BEARER_TOKEN}"
    if lang:
        params["language"] = lang
    try:
        return requests.get(f"{TMDB_BASE_URL}{path}", params=params, headers=headers, timeout=10)
    except Exception as exc:
        print(f"[tmdb] request error to {path}: {exc}", flush=True)
        return None


def _tmdb_image_url(path: str | None):
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{TMDB_IMAGE_BASE}{path}"


def _normalize_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    lang = lang.strip()
    if lang == "pt":
        return "pt-BR"
    if lang == "es":
        return "es-ES"
    return lang


def _fetch_detail(media_type: str, tmdb_id: Any, preferred_lang: str | None):
    resp = _tmdb_request(f"/{media_type}/{tmdb_id}", {"append_to_response": "external_ids"}, preferred_lang)
    if not resp or resp.status_code != 200:
        if resp:
            print(f"[tmdb] detail status={resp.status_code} body={resp.text[:400]}", flush=True)
        return None
    try:
        return resp.json()
    except Exception as exc:
        print(f"[tmdb] detail parse error: {exc} body={resp.text[:400]}", flush=True)
        return None


def buscar_info_tmdb(raw_title: str, lang: str = "") -> Optional[Dict[str, Any]]:
    """Busca TMDB com candidatos (guessit + heurística) e pontua melhor resultado."""
    if not (TMDB_API_KEY or TMDB_BEARER_TOKEN):
        print("[tmdb] credenciais ausentes (KEY_API_TMDB/TOKEN_API_TMDB)", flush=True)
        return None

    candidates, year = generate_candidates(raw_title)
    lang = _normalize_lang((lang or "").strip() or None)

    best_item: Tuple[Dict[str, Any], str, float] | None = None

    def run_search(lang_code: str | None, label: str, include_year: bool = True):
        nonlocal best_item
        for cand in candidates:
            search_params = {"query": cand, "include_adult": "false"}
            if include_year and year:
                search_params["year"] = year

            print(f"[tmdb] search '{cand}' year={year} lang='{label}'", flush=True)
            resp = _tmdb_request("/search/multi", search_params, lang_code)
            if not resp or resp.status_code != 200:
                if resp:
                    print(f"[tmdb] search status={resp.status_code} body={resp.text[:400]}", flush=True)
                continue

            try:
                results = resp.json().get("results") or []
            except Exception as exc:
                print(f"[tmdb] search parse error: {exc} body={resp.text[:400]}", flush=True)
                continue

            for item in results:
                media_type = item.get("media_type") or ("movie" if "title" in item else "tv")
                if media_type not in ("movie", "tv"):
                    continue
                score = score_tmdb_result(cand, year, item)
                if not best_item or score > best_item[2]:
                    best_item = (item, media_type, score)

    # 1ª passada: idioma solicitado
    run_search(lang, lang or "default", include_year=True)
    if not best_item:
        run_search(lang, (lang or "default") + "-no-year", include_year=False)
    # Fallback: busca em en-US se nada encontrado
    if not best_item:
        run_search(None, "fallback-en", include_year=True)
    if not best_item:
        run_search(None, "fallback-en-no-year", include_year=False)

    if not best_item:
        print("[tmdb] no candidate found", flush=True)
        return None

    item, media_type, _ = best_item
    tmdb_id = item.get("id")
    if not tmdb_id:
        return None

    detail = _fetch_detail(media_type, tmdb_id, lang)
    if not detail and lang:
        detail = _fetch_detail(media_type, tmdb_id, None)
    if not detail:
        return None

    imdb_id = detail.get("imdb_id") or detail.get("external_ids", {}).get("imdb_id")
    titulo = detail.get("title") or detail.get("name") or item.get("title") or item.get("name") or raw_title
    sinopse = detail.get("overview") or item.get("overview") or ""
    poster_path = detail.get("poster_path") or item.get("poster_path") or ""
    imagem = _tmdb_image_url(poster_path)

    generos = ""
    genres = detail.get("genres") or []
    if isinstance(genres, list):
        nomes = [g.get("name") for g in genres if isinstance(g, dict) and g.get("name")]
        generos = ", ".join(nomes)

    nota_val = detail.get("vote_average")
    nota = ""
    if isinstance(nota_val, (int, float)):
        nota = str(round(nota_val, 1))
    elif nota_val is not None:
        nota = str(nota_val)

    # fallback en-US se sinopse/imagem vazios
    if lang and (not sinopse or not imagem):
        fb = _fetch_detail(media_type, tmdb_id, None)
        if fb:
            sinopse = sinopse or fb.get("overview") or ""
            fb_poster = fb.get("poster_path")
            if not imagem and fb_poster:
                imagem = _tmdb_image_url(fb_poster)
            if not imdb_id:
                imdb_id = fb.get("imdb_id") or fb.get("external_ids", {}).get("imdb_id")
            if not generos:
                fb_genres = fb.get("genres") or []
                nomes = [g.get("name") for g in fb_genres if isinstance(g, dict) and g.get("name")]
                generos = ", ".join(nomes)

    return {
        "id_imdb": imdb_id,
        "titulo": html.unescape(titulo or ""),
        "sinopse": html.unescape(sinopse or ""),
        "imagem": imagem,
        "generos": generos,
        "nota": nota,
    }
