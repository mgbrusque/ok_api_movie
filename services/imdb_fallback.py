import html
import requests

from utils.title_cleaner import generate_candidates


def _safe_image(url: str | None) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return url


def _do_request(url, params, headers):
    try:
        return requests.get(url, params=params, headers=headers, timeout=10)
    except Exception as exc:
        print(f"[imdb-fallback] request error to {url}: {exc}", flush=True)
        return None


def buscar_info_imdb_fallback(titulo_raw: str):
    """
    Busca na API imdb.iamidiotareyoutoo.com (apenas en-US) como fallback para TMDB.
    Retorna dict compatível ou None.
    """
    base_url = "https://imdb.iamidiotareyoutoo.com"
    candidates, year = generate_candidates(titulo_raw)
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}

    for cand in candidates:
        q = cand if not year else f"{cand} {year}"
        print(f"[imdb-fallback] search '{q}'", flush=True)
        resp_search = _do_request(f"{base_url}/search", {"q": q}, headers)
        if not resp_search or resp_search.status_code != 200:
            # tenta http como fallback
            resp_search = _do_request(f"http://imdb.iamidiotareyoutoo.com/search", {"q": q}, headers)
        if not resp_search or resp_search.status_code != 200:
            continue
        try:
            search_data = resp_search.json()
        except Exception:
            continue

        imdb_id = None
        poster_search = ""
        if isinstance(search_data, dict):
            desc = search_data.get("description")
            if isinstance(desc, list) and desc:
                first = desc[0]
                if isinstance(first, dict):
                    imdb_id = first.get("#IMDB_ID") or first.get("IMDB_ID") or first.get("id")
                    poster_search = first.get("#IMG_POSTER") or first.get("IMG_POSTER") or first.get("image") or ""
            elif isinstance(desc, dict):
                imdb_id = desc.get("#IMDB_ID") or desc.get("IMDB_ID") or desc.get("id")
                poster_search = desc.get("#IMG_POSTER") or desc.get("IMG_POSTER") or desc.get("image") or ""
        elif isinstance(search_data, list) and search_data:
            first = search_data[0]
            if isinstance(first, dict):
                imdb_id = first.get("#IMDB_ID") or first.get("IMDB_ID") or first.get("id")
                poster_search = first.get("#IMG_POSTER") or first.get("IMG_POSTER") or first.get("image") or ""

        if isinstance(search_data, dict) and not imdb_id:
            imdb_id = search_data.get("IMDB_ID") or search_data.get("id")

        if not imdb_id and poster_search:
            return {
                "id_imdb": None,
                "titulo": html.unescape(cand),
                "sinopse": "",
                "imagem": _safe_image(poster_search),
                "generos": "",
                "nota": "",
            }
        if not imdb_id:
            continue

        resp_detail = _do_request(f"{base_url}/search", {"tt": imdb_id}, headers)
        if not resp_detail or resp_detail.status_code != 200:
            resp_detail = _do_request("http://imdb.iamidiotareyoutoo.com/search", {"tt": imdb_id}, headers)
        if not resp_detail or resp_detail.status_code != 200:
            if poster_search:
                return {
                    "id_imdb": imdb_id,
                    "titulo": html.unescape(cand),
                    "sinopse": "",
                    "imagem": _safe_image(poster_search),
                    "generos": "",
                    "nota": "",
                }
            continue

        try:
            detail = resp_detail.json()
        except Exception:
            detail = {}

        short = detail.get("short", {}) if isinstance(detail, dict) else {}
        titulo = short.get("name") or cand
        sinopse = short.get("description") or ""
        rating = ""
        if isinstance(short.get("aggregateRating"), dict):
            rating_val = short["aggregateRating"].get("ratingValue")
            if rating_val is not None:
                rating = str(rating_val)
        imagem = poster_search or short.get("image") or ""
        generos = ""
        genre_data = short.get("genre")
        if isinstance(genre_data, list):
            generos = ", ".join([g for g in genre_data if isinstance(g, str)])
        elif isinstance(genre_data, str):
            generos = genre_data

        return {
            "id_imdb": imdb_id,
            "titulo": html.unescape(titulo or cand),
            "sinopse": html.unescape(sinopse or ""),
            "imagem": _safe_image(imagem),
            "generos": generos,
            "nota": rating,
        }

    return None
