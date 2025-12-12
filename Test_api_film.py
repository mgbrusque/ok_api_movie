import argparse
import re
import unicodedata
import requests
import html


BASE_URL = "https://imdb.iamidiotareyoutoo.com"


def limpar_titulo_para_busca(titulo_raw: str):
    if not titulo_raw:
        return "", None
    titulo = titulo_raw
    try:
        titulo = re.sub(r"[\[\(\{].*?[\]\)\}]", " ", titulo)
    except re.error:
        titulo = titulo.replace("(", " ").replace(")", " ").replace("[", " ").replace("]", " ").replace("{", " ").replace("}", " ")
    lixo_tokens = [
        "1080p", "1080", "720p", "720", "2160p", "4k", "uhd",
        "h264", "x264", "x265", "hevc", "h265",
        "bluray", "blu-ray", "brrip", "hdrip", "webrip", "web-dl", "webdl",
        "dublado", "legendado", "dual audio", "dual_audio", "dub", "leg",
        "hdr", "hdr10", "remaster", "remastered", "extended", "directors cut",
        "cam", "dvdrip", "dvdscr"
    ]
    pattern_lixo = r"\b(" + "|".join(lixo_tokens) + r")\b"
    titulo = re.sub(pattern_lixo, " ", titulo, flags=re.IGNORECASE)
    ano = None
    ano_match = re.search(r"\b(19|20)\d{2}\b", titulo)
    if ano_match:
        ano = ano_match.group(0)
        titulo = titulo.replace(ano, " ")
    titulo = re.sub(r"[_.\-]+", " ", titulo)
    titulo = re.sub(r"[\"'`´“”‘’«»]+", " ", titulo)
    titulo = unicodedata.normalize("NFKC", titulo)
    titulo = re.sub(r"[^\w\s]", " ", titulo, flags=re.UNICODE)
    titulo = re.sub(r"\s+", " ", titulo).strip()
    return titulo, ano


def do_request(url, params, headers):
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        return resp
    except Exception as exc:
        print(f"[req] error {url} {exc}")
        return None


def buscar_info(titulo_raw: str, lang: str = ""):
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    lang = (lang or "").strip()
    if lang:
        headers["Accept-Language"] = lang

    titulo_limpo, ano = limpar_titulo_para_busca(titulo_raw)
    if not titulo_limpo:
        print("[info] titulo vazio apos limpeza")
        return
    q = titulo_limpo if not ano else f"{titulo_limpo} {ano}"
    print(f"[q] '{q}' lang='{lang}'")

    resp = do_request(f"{BASE_URL}/search", {"q": q}, headers)
    if not resp or resp.status_code != 200:
        print(f"[q] status={resp.status_code if resp else 'err'} body={resp.text[:400] if resp else ''}")
        resp = do_request(f"http://imdb.iamidiotareyoutoo.com/search", {"q": q}, headers)
    if not resp:
        print("[q] sem resposta")
        return
    print(f"[q] status={resp.status_code}")
    print(f"[q] body: {resp.text[:300]}")
    try:
        data = resp.json()
    except Exception as exc:
        print(f"[q] json error {exc}")
        return

    imdb_id = None
    poster = ""
    if isinstance(data, dict):
        desc = data.get("description")
        if isinstance(desc, list) and desc:
            first = desc[0]
            if isinstance(first, dict):
                imdb_id = first.get("#IMDB_ID") or first.get("IMDB_ID") or first.get("id")
                poster = first.get("#IMG_POSTER") or first.get("IMG_POSTER") or first.get("image") or ""
        elif isinstance(desc, dict):
            imdb_id = desc.get("#IMDB_ID") or desc.get("IMDB_ID") or desc.get("id")
            poster = desc.get("#IMG_POSTER") or desc.get("IMG_POSTER") or desc.get("image") or ""
    elif isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            imdb_id = first.get("#IMDB_ID") or first.get("IMDB_ID") or first.get("id")
            poster = first.get("#IMG_POSTER") or first.get("IMG_POSTER") or first.get("image") or ""

    print(f"[q] parsed id={imdb_id} poster={poster}")
    if not imdb_id:
        print("[q] nenhum imdb_id")
        return

    resp_d = do_request(f"{BASE_URL}/search", {"tt": imdb_id}, headers)
    if not resp_d or resp_d.status_code != 200:
        print(f"[tt] status={resp_d.status_code if resp_d else 'err'} body={resp_d.text[:400] if resp_d else ''}")
        resp_d = do_request("http://imdb.iamidiotareyoutoo.com/search", {"tt": imdb_id}, headers)
    if not resp_d:
        print("[tt] sem resposta")
        return
    print(f"[tt] status={resp_d.status_code}")
    print(f"[tt] body: {resp_d.text[:300]}")
    try:
        detail = resp_d.json()
    except Exception as exc:
        print(f"[tt] json error {exc}")
        return

    short = detail.get("short", {}) if isinstance(detail, dict) else {}
    titulo = short.get("name") or titulo_limpo
    sinopse = short.get("description") or ""
    rating = ""
    if isinstance(short.get("aggregateRating"), dict):
        rv = short["aggregateRating"].get("ratingValue")
        if rv is not None:
            rating = str(rv)
    generos = ""
    g = short.get("genre")
    if isinstance(g, list):
        generos = ", ".join([x for x in g if isinstance(x, str)])
    elif isinstance(g, str):
        generos = g
    imagem = poster or short.get("image") or ""

    print("\n[RESULT]")
    print("id_imdb:", imdb_id)
    print("titulo:", html.unescape(titulo or ""))
    print("sinopse:", html.unescape(sinopse or ""))
    print("imagem:", imagem)
    print("generos:", generos)
    print("nota:", rating)


def main():
    # Preencha aqui para testar rápido sem CLI
    default_titulo = "rambo"
    default_lang = "pt"

    parser = argparse.ArgumentParser(description="Teste de chamada IMDb API (iamidiotareyoutoo.com)")
    parser.add_argument("--titulo", default=default_titulo, help="Título bruto do filme/serie")
    parser.add_argument("--lang", default=default_lang, help="Idioma (Accept-Language)")
    args = parser.parse_args()

    if not args.titulo:
        print("Informe --titulo ou defina default_titulo no código.")
        return

    buscar_info(args.titulo, args.lang)


if __name__ == "__main__":
    main()
