import logging
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from services.db import get_conn
from services.imdb_fallback import buscar_info_imdb_fallback
from services.ok_client import buscar_videos, extrair_link_download
from services.tmdb_client import buscar_info_tmdb
from services.video_repository import buscar_videos_bd
from utils.media import normalize_image_url

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def get_cloudflare_beacon_token() -> str | None:
    """Returns Cloudflare Web Analytics beacon token if configured."""
    token = (os.environ.get("CLOUDFLARE_BEACON_TOKEN") or "").strip()
    return token or None


def use_vercel_analytics() -> bool:
    """
    Allows enabling Vercel Web Analytics via env flag.
    This works only when the app runs on Vercel (script served at /_vercel/insights/script.js).
    """
    return (os.environ.get("ENABLE_VERCEL_ANALYTICS") or "").strip().lower() in {"1", "true", "yes"}


@app.route("/")
def index():
    return render_template(
        "index.html",
        cf_beacon_token=get_cloudflare_beacon_token(),
        vercel_analytics=use_vercel_analytics(),
    )


@app.route("/buscar", methods=["POST"])
def buscar():
    query = request.form.get("query", "")
    offset = int(request.form.get("offset", 0))
    duration = request.form.get("duration", "")
    hd_quality = request.form.get("hd", "")
    fonte = request.form.get("fonte", "API")
    faixa = request.form.get("duration_bd", "")
    ordem = request.form.get("order_bd", "")

    videos = []
    total_api = 0
    total_bd = 0

    if fonte in ["API"]:
        resultado_api = buscar_videos(query, offset, duration, hd_quality)
        videos.extend(resultado_api["videos"])
        total_api = resultado_api["totalCount"]

    if fonte in ["BD"]:
        resultado_bd = buscar_videos_bd(query, offset, faixa=faixa, ordem=ordem)
        videos.extend(resultado_bd["videos"])
        total_bd = resultado_bd["totalCount"]

    unicos = {}
    for video in videos:
        if video["id"] not in unicos:
            unicos[video["id"]] = video

    videos_unicos = list(unicos.values())

    return jsonify({"videos": videos_unicos, "totalCount": total_api + total_bd})


@app.route("/download/<video_id>", methods=["GET"])
def download(video_id):
    try:
        prefer = request.args.get("h")
        prefer_height = int(prefer) if prefer and prefer.isdigit() else None
        data = extrair_link_download(video_id, prefer_height)
        if data.get("streaming"):
            return jsonify({"error": "Download direto nao disponivel (apenas streaming HLS/DASH)."}), 404
        return jsonify(data)
    except Exception as exc:  # pylint: disable=broad-except
        logging.exception("Erro ao preparar download para %s", video_id)
        return jsonify({"error": str(exc)}), 500


@app.route("/info/<video_id>", methods=["GET"])
def info(video_id):
    """
    Busca dados no TMDB (movie/tv) e salva/retorna infofilmes.
    Respeita idioma via param lang (pt-BR/es-ES/en-US).
    """
    if not video_id:
        return jsonify({"error": "video_id obrigatorio"}), 400

    titulo_raw = request.args.get("title", "")
    thumb_raw = request.args.get("thumb", "")
    thumb_url = normalize_image_url(thumb_raw)
    lang = (request.args.get("lang") or "").strip() or None

    logging.info("[info] req id=%s title='%s' lang='%s'", video_id, titulo_raw, lang)

    info_db = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id_imdb, titulo, sinopse, imagem, generos, nota, language
            FROM infofilmes
            WHERE id = %s
            """,
            (video_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            logging.info("[info] found cache for %s", video_id)
            info_db = {
                "id_imdb": row[0],
                "titulo": row[1],
                "sinopse": row[2],
                "imagem": normalize_image_url(row[3]),
                "generos": row[4],
                "nota": row[5],
                "language": row[6],
            }
    except Exception as exc:  # pylint: disable=broad-except
        logging.warning("[info] cache lookup error: %s", exc)
        info_db = None

    if info_db and (not lang or not info_db.get("language") or info_db.get("language") == lang):
        info_db["cached"] = True
        return jsonify(info_db)

    if not titulo_raw.strip() or "carregando" in titulo_raw.lower():
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT nome FROM filmes WHERE id = %s LIMIT 1", (video_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row[0]:
                titulo_raw = row[0]
                logging.info("[info] title fetched from filmes: '%s'", titulo_raw)
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("[info] title fetch error: %s", exc)

    info_api = None
    if titulo_raw.strip():
        info_api = buscar_info_tmdb(titulo_raw, lang or "")
        if not info_api:
            info_api = buscar_info_imdb_fallback(titulo_raw)
        logging.info("[info] api result keys=%s", list(info_api.keys()) if info_api else None)
    else:
        logging.info("[info] skipped api call (empty title)")

    data = info_api or info_db
    if not data:
        data = {
            "id_imdb": None,
            "titulo": titulo_raw or "",
            "sinopse": "",
            "imagem": thumb_url,
            "generos": "",
            "nota": "",
            "language": lang,
            "empty": True,
        }

    best_image = data.get("imagem") or thumb_url
    data["imagem"] = best_image
    data["language"] = lang or data.get("language")
    data["cached"] = info_api is None and info_db is not None

    should_persist = bool(info_api) and not data.get("empty")
    if should_persist:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO infofilmes (id, id_imdb, titulo, sinopse, imagem, generos, nota, language)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    id_imdb = EXCLUDED.id_imdb,
                    titulo = EXCLUDED.titulo,
                    sinopse = EXCLUDED.sinopse,
                    imagem = EXCLUDED.imagem,
                    generos = EXCLUDED.generos,
                    nota = EXCLUDED.nota,
                    language = EXCLUDED.language
            """,
                (
                    video_id,
                    data.get("id_imdb"),
                    data.get("titulo"),
                    data.get("sinopse"),
                    best_image,
                    data.get("generos"),
                    data.get("nota"),
                    lang or data.get("language"),
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
            logging.info("[info] persisted %s", video_id)
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("[info] persist error %s", exc)
    else:
        logging.info("[info] nothing to persist (empty or no api/db)")

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True)
